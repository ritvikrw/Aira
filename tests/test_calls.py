"""
Tests for the calls router using an in-memory SQLite database.
"""
import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import String, Text, Integer, TIMESTAMP, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional

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


@pytest.fixture(scope="module")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(db_session):
    """Create TestClient with overridden DB."""
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    from database import get_db
    from routes.calls import router

    app = FastAPI()
    app.include_router(router)

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_create_call(client):
    """POST /calls/ creates a call and returns session_id."""
    resp = client.post("/calls/", json={"session_id": "sess-create-1", "caller_id": "+1234"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"] == "sess-create-1"
    assert data["status"] == "active"


def test_create_call_existing_returns_existing(client):
    """POST /calls/ with existing session_id returns existing call."""
    client.post("/calls/", json={"session_id": "dup-sess-100"})
    resp = client.post("/calls/", json={"session_id": "dup-sess-100"})
    assert resp.status_code == 201
    assert resp.json()["session_id"] == "dup-sess-100"


def test_end_call(client):
    """POST /calls/{id}/end marks call as ended (new session without prior start)."""
    resp = client.post("/calls/brand-new-sess-end/end")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "brand-new-sess-end"


def test_list_calls(client):
    """GET /calls/ returns a list."""
    client.post("/calls/", json={"session_id": "list-sess-200"})
    resp = client.get("/calls/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_cleanup_stale(client):
    """POST /calls/cleanup-stale returns fixed count."""
    resp = client.post("/calls/cleanup-stale")
    assert resp.status_code == 200
    data = resp.json()
    assert "fixed" in data
    assert isinstance(data["fixed"], int)
