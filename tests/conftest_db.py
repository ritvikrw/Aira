"""
Shared SQLite test database setup for API route tests.
Provides TestBase, all SQLite-compatible model definitions, and helper fixtures.
"""
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import String, Text, Integer, Float, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestBase(DeclarativeBase):
    pass


class CallLogTest(TestBase):
    __tablename__ = "call_logs"
    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    caller_id: Mapped[Optional[str]] = mapped_column(String(128))
    caller_name: Mapped[Optional[str]] = mapped_column(String(256))
    caller_phone: Mapped[Optional[str]] = mapped_column(String(32))
    room_name: Mapped[Optional[str]] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="active")
    call_start_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    call_end_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    call_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)


class TranscriptTest(TestBase):
    __tablename__ = "transcripts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64))
    speaker: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)


class CallSummaryTest(TestBase):
    __tablename__ = "call_summaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64))
    summary_text: Mapped[str] = mapped_column(Text)
    key_topics: Mapped[Optional[str]] = mapped_column(Text)
    action_items: Mapped[Optional[str]] = mapped_column(Text)
    call_category: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)


class AgentSettingTest(TestBase):
    __tablename__ = "agent_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class CallMetricsTest(TestBase):
    __tablename__ = "call_metrics"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64))
    llm_prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    llm_completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    llm_ttft_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    llm_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tts_provider: Mapped[Optional[str]] = mapped_column(String(64), default=None)
    tts_characters: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tts_ttfb_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    tts_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    stt_audio_duration_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    stt_ttft_ms: Mapped[Optional[float]] = mapped_column(Float, default=None)
    stt_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
