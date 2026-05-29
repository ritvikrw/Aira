from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, ARRAY, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    caller_id: Mapped[Optional[str]] = mapped_column(String(128))
    caller_name: Mapped[Optional[str]] = mapped_column(String(256))
    caller_phone: Mapped[Optional[str]] = mapped_column(String(32))
    room_name: Mapped[Optional[str]] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), default="active")
    call_start_time: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    call_end_time: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    call_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)


class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    speaker: Mapped[str] = mapped_column(String(16))  # 'user' or 'agent'
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class CallSummary(Base):
    __tablename__ = "call_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    summary_text: Mapped[str] = mapped_column(Text)
    key_topics: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    action_items: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text))
    call_category: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class AgentSetting(Base):
    __tablename__ = "agent_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class CallMetrics(Base):
    __tablename__ = "call_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    # LLM
    llm_prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    llm_completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    llm_ttft_ms: Mapped[Optional[float]] = mapped_column(default=None)         # time to first token (ms)
    llm_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    # TTS
    tts_provider: Mapped[Optional[str]] = mapped_column(String(64), default=None)  # e.g. "OpenAI / tts-1"
    tts_characters: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tts_ttfb_ms: Mapped[Optional[float]] = mapped_column(default=None)         # time to first byte (ms)
    tts_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    # STT
    stt_audio_duration_ms: Mapped[Optional[float]] = mapped_column(default=None)
    stt_ttft_ms: Mapped[Optional[float]] = mapped_column(default=None)          # batch processing latency (ms)
    stt_requests: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    error_msg: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
