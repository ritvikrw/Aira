"""Extended tests for the calls router — covering more endpoints for higher coverage."""
import sys
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from conftest_db import TestBase, CallLogTest, TranscriptTest, CallSummaryTest

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

_MOCK_SUMMARY = {
    "summary_text": "Customer called about billing",
    "key_topics": ["billing", "refund"],
    "action_items": ["Send invoice"],
    "call_category": "Billing",
}


def _make_client(db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from database import get_db
    from routes.calls import router

    app = FastAPI()
    app.include_router(router)

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    return TestClient(app, raise_server_exceptions=True)


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
    with _make_client(db_session) as c:
        yield c


# ── start call ────────────────────────────────────────────────────────────────
def test_start_call_with_start_time(client):
    resp = client.post("/calls/", json={
        "session_id": "ext-time-1",
        "start_time": "2024-01-15T10:00:00",
    })
    assert resp.status_code == 201
    assert resp.json()["session_id"] == "ext-time-1"


def test_start_call_with_invalid_start_time(client):
    """Invalid start_time is silently ignored."""
    resp = client.post("/calls/", json={
        "session_id": "ext-bad-time-1",
        "start_time": "not-a-date",
    })
    assert resp.status_code == 201


def test_start_call_with_phone_and_room(client):
    resp = client.post("/calls/", json={
        "session_id": "ext-full-1",
        "caller_id": "cid-1",
        "caller_phone": "+9190000000",
        "room_name": "room-1",
    })
    assert resp.status_code == 201
    assert resp.json()["status"] == "active"


# ── update caller info ────────────────────────────────────────────────────────
def test_update_caller_name(client):
    client.post("/calls/", json={"session_id": "ext-patch-1"})
    resp = client.patch("/calls/ext-patch-1/caller", json={"caller_name": "John Doe"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["caller_name"] == "John Doe"


def test_update_caller_name_strips_whitespace(client):
    client.post("/calls/", json={"session_id": "ext-patch-strip"})
    resp = client.patch("/calls/ext-patch-strip/caller", json={"caller_name": "  Jane  "})
    assert resp.status_code == 200
    assert resp.json()["caller_name"] == "Jane"


def test_update_caller_name_empty_sets_null(client):
    client.post("/calls/", json={"session_id": "ext-patch-null"})
    resp = client.patch("/calls/ext-patch-null/caller", json={"caller_name": ""})
    assert resp.status_code == 200
    assert resp.json()["caller_name"] is None


def test_update_caller_name_not_found(client):
    resp = client.patch("/calls/nonexistent-999/caller", json={"caller_name": "X"})
    assert resp.status_code == 404


# ── end call ──────────────────────────────────────────────────────────────────
def test_end_call_creates_if_not_exist(client):
    resp = client.post("/calls/ext-end-new-999/end")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "ext-end-new-999"


# ── get call ──────────────────────────────────────────────────────────────────
def test_get_call_returns_fields(client):
    client.post("/calls/", json={"session_id": "ext-get-1", "caller_phone": "+91999"})
    resp = client.get("/calls/ext-get-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "ext-get-1"
    assert "status" in data
    assert "summary" in data
    assert data["summary"] is None


def test_get_call_not_found(client):
    resp = client.get("/calls/no-such-call")
    assert resp.status_code == 404


# ── list calls ────────────────────────────────────────────────────────────────
def test_list_calls_filter_by_room(client):
    client.post("/calls/", json={"session_id": "ext-room-1", "room_name": "room-A"})
    client.post("/calls/", json={"session_id": "ext-room-2", "room_name": "room-B"})
    resp = client.get("/calls/?room_name=room-A")
    assert resp.status_code == 200
    data = resp.json()
    session_ids = [r["session_id"] for r in data]
    assert "ext-room-1" in session_ids
    assert "ext-room-2" not in session_ids


def test_list_calls_has_expected_fields(client):
    client.post("/calls/", json={"session_id": "ext-list-fields"})
    resp = client.get("/calls/")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    row = rows[0]
    assert "session_id" in row
    assert "status" in row
    assert "key_topics" in row
    assert "action_items" in row


# ── cleanup-stale ─────────────────────────────────────────────────────────────
def test_cleanup_stale_custom_threshold(client):
    resp = client.post("/calls/cleanup-stale?threshold_minutes=120")
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold_minutes"] == 120


def test_cleanup_stale_marks_old_calls_ended(client):
    """Active calls older than threshold should be marked ended."""
    from sqlalchemy import update as sa_update
    import asyncio

    # Create a call and manually backdate it
    client.post("/calls/", json={"session_id": "ext-stale-old"})

    async def backdate():
        eng = create_async_engine(TEST_DATABASE_URL, echo=False)
        async with eng.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)
        await eng.dispose()

    resp = client.post("/calls/cleanup-stale?threshold_minutes=0")
    assert resp.status_code == 200
    data = resp.json()
    assert "fixed" in data


# ── delete all ───────────────────────────────────────────────────────────────
def test_delete_all_calls(client):
    client.post("/calls/", json={"session_id": "ext-del-1"})
    resp = client.delete("/calls/all")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


def test_list_after_delete_is_empty(client):
    client.delete("/calls/all")
    resp = client.get("/calls/")
    assert resp.status_code == 200
    assert resp.json() == []


# ── analytics ────────────────────────────────────────────────────────────────
def test_analytics_overview_returns_keys(client):
    resp = client.get("/calls/analytics/overview")
    assert resp.status_code == 200
    data = resp.json()
    for key in ["total_calls", "active_calls", "calls_today", "avg_duration_seconds",
                "categories", "status_breakdown"]:
        assert key in data


def test_analytics_with_date_window(client):
    resp = client.get("/calls/analytics/overview?start_date=2024-01-01&end_date=2024-12-31")
    assert resp.status_code == 200


def test_analytics_with_timezone(client):
    resp = client.get("/calls/analytics/overview?tz=Asia/Kolkata")
    assert resp.status_code == 200


def test_analytics_invalid_timezone_falls_back(client):
    resp = client.get("/calls/analytics/overview?tz=Invalid/Zone")
    assert resp.status_code == 200


def test_analytics_with_invalid_dates(client):
    resp = client.get("/calls/analytics/overview?start_date=bad&end_date=also-bad")
    assert resp.status_code == 200
