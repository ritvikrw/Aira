"""Tests for the transcripts router."""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from conftest_db import TestBase, TranscriptTest

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    if True:
        from database import get_db
        from routes.transcripts import router

        app = FastAPI()
        app.include_router(router)

        async def override():
            yield db_session

        app.dependency_overrides[get_db] = override

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c


def test_create_transcript_user(client):
    resp = client.post("/transcripts/", json={
        "session_id": "tx-sess-1",
        "speaker": "user",
        "message": "Hello"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["session_id"] == "tx-sess-1"
    assert data["speaker"] == "user"


def test_create_transcript_agent(client):
    resp = client.post("/transcripts/", json={
        "session_id": "tx-sess-2",
        "speaker": "agent",
        "message": "How can I help you?"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["speaker"] == "agent"


def test_create_transcript_invalid_speaker(client):
    resp = client.post("/transcripts/", json={
        "session_id": "tx-sess-3",
        "speaker": "unknown",
        "message": "Bad speaker"
    })
    assert resp.status_code == 400


def test_get_transcripts_empty(client):
    resp = client.get("/transcripts/nonexistent-session")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_transcripts_returns_list(client):
    # Create two transcripts
    client.post("/transcripts/", json={"session_id": "tx-list-1", "speaker": "user", "message": "Hi"})
    client.post("/transcripts/", json={"session_id": "tx-list-1", "speaker": "agent", "message": "Hello"})

    resp = client.get("/transcripts/tx-list-1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


def test_get_transcripts_has_correct_fields(client):
    client.post("/transcripts/", json={"session_id": "tx-fields-1", "speaker": "user", "message": "Test message"})
    resp = client.get("/transcripts/tx-fields-1")
    assert resp.status_code == 200
    item = resp.json()[0]
    assert "id" in item
    assert "speaker" in item
    assert "message" in item
    assert item["message"] == "Test message"


def test_get_transcripts_ordered_by_created_at(client):
    client.post("/transcripts/", json={"session_id": "tx-order-1", "speaker": "user", "message": "First"})
    client.post("/transcripts/", json={"session_id": "tx-order-1", "speaker": "agent", "message": "Second"})
    resp = client.get("/transcripts/tx-order-1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # IDs should be ascending
    assert data[0]["id"] < data[1]["id"]
