import redis.asyncio as aioredis
from typing import Optional
import json
from pathlib import Path
from app.config.setting import settings
from app.schemas.response import Message
from app.utils.log_util import logger
from uuid import uuid4
from datetime import datetime
from typing import Any, Optional

from app.db.database import AsyncSessionLocal
from app.db.repositories import MessageRepository, RunRepository, RunUpsert


class RedisManager:
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self._client: Optional[aioredis.Redis] = None
        # 创建消息存储目录
        self.messages_dir = Path("logs/messages")
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    async def get_client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = aioredis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
            )
        try:
            await self._client.ping()
            logger.info(f"Redis 连接建立成功: {self.redis_url}")
            return self._client
        except Exception as e:
            logger.error(f"无法连接到Redis: {str(e)}")
            raise

    async def set(self, key: str, value: str):
        """设置Redis键值对"""
        client = await self.get_client()
        await client.set(key, value)
        await client.expire(key, 36000)

    async def _save_message_to_file(self, task_id: str, message: Message):
        """将消息保存到文件中，同一任务的消息保存在同一个文件中"""
        try:
            # 确保目录存在
            self.messages_dir.mkdir(exist_ok=True)

            # 使用任务ID作为文件名
            file_path = self.messages_dir / f"{task_id}.json"

            # 读取现有消息（如果文件存在）
            messages = []
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    messages = json.load(f)

            # 添加新消息
            message_data = message.model_dump()
            messages.append(message_data)

            # 保存所有消息到文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

            logger.debug(f"消息已追加到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存消息到文件失败: {str(e)}")
            # 不抛出异常，确保主流程不受影响

    async def publish_message(self, task_id: str, message: Message):
        """兼容旧接口：发布消息到 task 频道，并写文件 + SQLite（作为 legacy run）"""
        client = await self.get_client()
        channel = f"task:{task_id}:messages"
        try:
            message_json = message.model_dump_json()
            await client.publish(channel, message_json)
            logger.debug(
                f"消息已发布到频道 {channel}:mes_type:{message.msg_type}:msg_content:{message.content}"
            )
            # 保存消息到文件
            await self._save_message_to_file(task_id, message)

            # 同时发布到新的 run 频道，并落库（project/run 模式：优先从 Redis 取 project_id 映射）
            try:
                mapped_project_id = await client.get(f"run_project:{task_id}")
            except Exception:
                mapped_project_id = None

            project_id = mapped_project_id or "legacy"
            await self.publish_event(
                project_id=project_id,
                run_id=task_id,
                event_type="agent.chunk" if message.msg_type != "system" else "run.status",
                message=message,
                trace_id=None,
                agent=None,
                also_publish_legacy_task_channel=False,
            )
        except Exception as e:
            logger.error(f"发布消息失败: {str(e)}")
            raise

    async def publish_event(
        self,
        *,
        project_id: str,
        run_id: str,
        event_type: str,
        message: Message,
        trace_id: Optional[str] = None,
        agent: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        also_publish_legacy_task_channel: bool = False,
    ) -> dict[str, Any]:
        """
        新接口：以 project/run 为维度发布事件（Redis 流式）并写入 SQLite（历史）。
        兼容要求：顶层仍保留 msg_type/content/agent_type/tool_name 等字段。
        """
        client = await self.get_client()
        event_id = str(uuid4())
        payload = payload or {}

        envelope: dict[str, Any] = {
            # 兼容旧前端字段
            **message.model_dump(),
            # 新字段
            "event_id": event_id,
            "trace_id": trace_id,
            "project_id": project_id,
            "run_id": run_id,
            "event_type": event_type,
            "agent": agent,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1) Redis publish（流式）
        run_channel = f"run:{run_id}:events"
        await client.publish(run_channel, json.dumps(envelope, ensure_ascii=False))

        # 可选：同时发布旧 task 频道，方便渐进迁移
        if also_publish_legacy_task_channel:
            legacy_channel = f"task:{run_id}:messages"
            await client.publish(legacy_channel, json.dumps(envelope, ensure_ascii=False))

        # 2) SQLite append（历史）
        try:
            async with AsyncSessionLocal() as session:
                await RunRepository(session).upsert(
                    RunUpsert(project_id=project_id, run_id=run_id, status="running")
                )
                await MessageRepository(session).append_event(
                    id=event_id,
                    project_id=project_id,
                    run_id=run_id,
                    trace_id=trace_id,
                    event_type=event_type,
                    agent=agent,
                    msg_type=getattr(message, "msg_type", None),
                    agent_type=getattr(message, "agent_type", None),
                    tool_name=getattr(message, "tool_name", None),
                    content=getattr(message, "content", None),
                    payload=envelope,
                )
        except Exception as e:
            logger.error(f"SQLite 追加历史消息失败（不阻断主流程）: {e}")

        return envelope

    async def subscribe_to_run(self, run_id: str):
        """订阅特定 run 的事件流"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"run:{run_id}:events")
        return pubsub

    async def subscribe_to_task(self, task_id: str):
        """订阅特定任务的消息"""
        client = await self.get_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"task:{task_id}:messages")
        return pubsub

    async def close(self):
        """关闭Redis连接"""
        if self._client:
            await self._client.close()
            self._client = None


redis_manager = RedisManager()
