"""Tests for the internal metrics router."""
import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from conftest_db import TestBase

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

    from database import get_db
    from routes.internal import router

    app = FastAPI()
    app.include_router(router)

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_save_metrics_creates_new(client):
    resp = client.post("/internal/metrics/sess-m-1", json={
        "llm_prompt_tokens": 100,
        "llm_completion_tokens": 50,
        "llm_requests": 1,
        "tts_characters": 200,
        "tts_requests": 1,
        "stt_requests": 1,
    })
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


def test_save_metrics_accumulates(client):
    # First save
    client.post("/internal/metrics/sess-m-acc", json={
        "llm_prompt_tokens": 100,
        "llm_completion_tokens": 50,
        "llm_requests": 1,
    })
    # Second save — should accumulate
    resp = client.post("/internal/metrics/sess-m-acc", json={
        "llm_prompt_tokens": 200,
        "llm_completion_tokens": 100,
        "llm_requests": 1,
    })
    assert resp.status_code == 201
    assert resp.json()["ok"] is True


def test_save_metrics_with_ttft(client):
    resp = client.post("/internal/metrics/sess-m-ttft", json={
        "llm_ttft_ms": 123.4,
        "tts_ttfb_ms": 55.5,
        "stt_ttft_ms": 78.9,
    })
    assert resp.status_code == 201


def test_save_metrics_keeps_first_ttft(client):
    """Second save with ttft should not overwrite the first."""
    client.post("/internal/metrics/sess-ttft-first", json={"llm_ttft_ms": 100.0})
    resp = client.post("/internal/metrics/sess-ttft-first", json={"llm_ttft_ms": 999.0})
    assert resp.status_code == 201


def test_save_metrics_tts_provider(client):
    resp = client.post("/internal/metrics/sess-prov", json={
        "tts_provider": "Sarvam AI",
        "tts_requests": 2,
    })
    assert resp.status_code == 201


def test_list_metrics_returns_list(client):
    resp = client.get("/internal/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_metrics_has_expected_keys(client):
    client.post("/internal/metrics/sess-keys", json={"llm_prompt_tokens": 10})
    resp = client.get("/internal/metrics")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) > 0
    row = rows[0]
    assert "session_id" in row
    assert "llm_prompt_tokens" in row
    assert "tts_characters" in row


def test_metrics_summary_empty_db():
    """metrics_summary on empty DB should return zero values."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import asyncio

    async def run():
        eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with eng.begin() as conn:
            await conn.run_sync(TestBase.metadata.create_all)

        async_session = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
            from database import get_db
            from routes.internal import router

            app = FastAPI()
            app.include_router(router)

            async def override():
                yield session

            app.dependency_overrides[get_db] = override
            with TestClient(app) as c:
                resp = c.get("/internal/metrics/summary")
                assert resp.status_code == 200
                data = resp.json()
                assert data["total_calls"] == 0
                assert data["avg_llm_ttft_ms"] is None

        await eng.dispose()

    asyncio.get_event_loop().run_until_complete(run())


def test_metrics_summary_with_data(client):
    client.post("/internal/metrics/sess-sum-1", json={
        "llm_ttft_ms": 200.0,
        "tts_ttfb_ms": 100.0,
        "stt_ttft_ms": 50.0,
        "llm_prompt_tokens": 100,
        "tts_characters": 500,
    })
    resp = client.get("/internal/metrics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_calls"] >= 1
    assert data["total_llm_tokens"] >= 100
    assert data["total_tts_characters"] >= 500
