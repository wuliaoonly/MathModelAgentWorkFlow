from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MessageRecord, Run


@dataclass
class RunUpsert:
    project_id: str
    run_id: str
    status: str = "running"
    title: Optional[str] = None


class RunRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, run: RunUpsert) -> None:
        existing = await self.session.get(Run, run.run_id)
        if existing is None:
            self.session.add(
                Run(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    status=run.status,
                    title=run.title,
                )
            )
        else:
            existing.project_id = run.project_id
            existing.status = run.status
            existing.title = run.title
        await self.session.commit()


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def append_event(
        self,
        *,
        id: str,
        project_id: str,
        run_id: str,
        trace_id: Optional[str],
        event_type: str,
        agent: Optional[str],
        msg_type: Optional[str],
        agent_type: Optional[str],
        tool_name: Optional[str],
        content: Optional[str],
        payload: dict[str, Any],
        created_at: Optional[datetime] = None,
    ) -> None:
        rec = MessageRecord(
            id=id,
            project_id=project_id,
            run_id=run_id,
            trace_id=trace_id,
            event_type=event_type,
            agent=agent,
            msg_type=msg_type,
            agent_type=agent_type,
            tool_name=tool_name,
            content=content,
            payload_json=json.dumps(payload, ensure_ascii=False),
            created_at=created_at or datetime.utcnow(),
        )
        self.session.add(rec)
        await self.session.commit()

    async def list_by_run(
        self, *, project_id: str, run_id: str, limit: int = 2000
    ) -> list[dict[str, Any]]:
        stmt = (
            select(MessageRecord)
            .where(MessageRecord.project_id == project_id, MessageRecord.run_id == run_id)
            .order_by(MessageRecord.created_at.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        results: list[dict[str, Any]] = []
        for r in rows:
            try:
                payload = json.loads(r.payload_json or "{}")
            except Exception:
                payload = {}

            # 返回“兼容旧前端”的消息形状：顶层仍保留 msg_type/content/agent_type/tool_name 等字段
            msg: dict[str, Any] = {
                "id": r.id,
                "msg_type": r.msg_type,
                "content": r.content,
            }
            if r.agent_type:
                msg["agent_type"] = r.agent_type
            if r.tool_name:
                msg["tool_name"] = r.tool_name

            # 新字段（project/run + event envelope）
            msg.update(
                {
                    "event_id": r.id,
                    "trace_id": r.trace_id,
                    "project_id": r.project_id,
                    "run_id": r.run_id,
                    "event_type": r.event_type,
                    "agent": r.agent,
                    "payload": payload,
                    "created_at": r.created_at.isoformat(),
                }
            )
            results.append(msg)
        return results

