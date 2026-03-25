from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from app.services.redis_manager import redis_manager
from app.schemas.response import SystemMessage
import asyncio
from app.services.ws_manager import ws_manager
from app.utils.log_util import logger
import json
from pathlib import Path

router = APIRouter()


async def send_history_messages(websocket: WebSocket, task_id: str):
    """
    发送历史消息到 WebSocket（用于重连时恢复消息）
    """
    try:
        messages_file = Path("logs/messages") / f"{task_id}.json"
        
        if not messages_file.exists():
            logger.info(f"任务 {task_id} 没有历史消息文件")
            return
        
        with open(messages_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
        
        logger.info(f"🔄 开始发送 {len(messages)} 条历史消息到 WebSocket")
        
        # 逐条发送历史消息
        for msg in messages:
            if ws_manager.is_connected(websocket):
                await ws_manager.send_personal_message_json(msg, websocket)
                await asyncio.sleep(0.01)  # 小延迟避免消息过快
            else:
                logger.warning("WebSocket 连接已断开，停止发送历史消息")
                break
        
        logger.info(f"✅ 历史消息发送完成")
    
    except Exception as e:
        logger.error(f"发送历史消息失败: {e}")
        # 不抛出异常，继续正常流程


@router.websocket("/task/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    logger.info(f"WebSocket 尝试连接 task_id: {task_id}")
    
    pubsub = None
    
    try:
        # 检查任务是否存在（先检查 Redis，再检查文件系统）
        redis_async_client = await redis_manager.get_client()
        task_exists_in_redis = await redis_async_client.exists(f"task_id:{task_id}")
        
        # 如果 Redis 中不存在，检查工作目录是否存在
        if not task_exists_in_redis:
            work_dir = Path("project/work_dir") / task_id
            if not work_dir.exists():
                logger.warning(f"Task not found in Redis or filesystem: {task_id}")
                await websocket.close(code=1008, reason="Task not found")
                return
            else:
                logger.info(f"Task {task_id} found in filesystem (Redis expired)")
                # 任务存在于文件系统，允许连接（用于查看历史任务）
        
        logger.info(f"WebSocket connected for task: {task_id}")

        # 建立 WebSocket 连接
        await ws_manager.connect(websocket)
        websocket.timeout = 500
        logger.info(f"WebSocket connection status: {websocket.client}")

        # 🔥 关键修复：先发送所有历史消息（重连时恢复）
        await send_history_messages(websocket, task_id)

        # 订阅 Redis 频道（订阅后才能接收新消息）
        pubsub = await redis_manager.subscribe_to_task(task_id)
        logger.info(f"Subscribed to Redis channel: task:{task_id}:messages")

        # 主消息循环 - 接收并转发实时消息
        while ws_manager.is_connected(websocket):
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if msg and msg.get("data"):
                    logger.debug(f"Received message from Redis: {msg}")
                    try:
                        msg_dict = json.loads(msg["data"])
                        await ws_manager.send_personal_message_json(msg_dict, websocket)
                        logger.debug(f"Sent message to WebSocket: {msg_dict}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON 解析错误: {e}, 原始数据: {msg.get('data')}")
                    except Exception as e:
                        logger.error(f"发送消息时出错: {e}")
                        # 连接可能已断开，退出循环
                        if not ws_manager.is_connected(websocket):
                            break
                
                await asyncio.sleep(0.1)

            except WebSocketDisconnect:
                logger.info(f"WebSocket 客户端主动断开连接: {task_id}")
                break
            except asyncio.CancelledError:
                logger.info(f"WebSocket 任务被取消: {task_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket 循环中出错: {e}")
                # 检查连接是否仍然有效
                if not ws_manager.is_connected(websocket):
                    logger.info("WebSocket 连接已失效，退出循环")
                    break
                await asyncio.sleep(1)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开连接: {task_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误: {e}", exc_info=True)
    finally:
        # 清理资源
        if pubsub:
            try:
                await pubsub.unsubscribe(f"task:{task_id}:messages")
                logger.info(f"已取消订阅 Redis 频道: task:{task_id}:messages")
            except Exception as e:
                logger.error(f"取消订阅时出错: {e}")
        
        ws_manager.disconnect(websocket)
        logger.info(f"WebSocket 连接已关闭: {task_id}")
