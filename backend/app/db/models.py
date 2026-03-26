from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32), default="running")
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: dt.datetime.utcnow()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=False),
        default=lambda: dt.datetime.utcnow(),
        onupdate=lambda: dt.datetime.utcnow(),
    )


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)

    trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    agent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    msg_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=False), default=lambda: dt.datetime.utcnow(), index=True
    )

