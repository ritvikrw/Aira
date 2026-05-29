"""Tests for the settings router."""
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
    from routes.settings import router

    app = FastAPI()
    app.include_router(router)

    async def override():
        yield db_session

    app.dependency_overrides[get_db] = override

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_list_voices_returns_list(client):
    resp = client.get("/settings/voices")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_list_voices_has_required_fields(client):
    resp = client.get("/settings/voices")
    voice = resp.json()[0]
    assert "voice_id" in voice
    assert "name" in voice
    assert "description" in voice


def test_list_voices_includes_sarvam(client):
    resp = client.get("/settings/voices")
    ids = [v["voice_id"] for v in resp.json()]
    assert any(vid.startswith("sarvam:") for vid in ids)


def test_list_voices_includes_openai(client):
    resp = client.get("/settings/voices")
    ids = [v["voice_id"] for v in resp.json()]
    assert "nova" in ids or "alloy" in ids


def test_list_languages_returns_list(client):
    resp = client.get("/settings/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_list_languages_includes_english(client):
    resp = client.get("/settings/languages")
    codes = [l["code"] for l in resp.json()]
    assert "en-IN" in codes


def test_list_languages_includes_hindi(client):
    resp = client.get("/settings/languages")
    codes = [l["code"] for l in resp.json()]
    assert "hi-IN" in codes


def test_list_languages_has_required_fields(client):
    resp = client.get("/settings/languages")
    lang = resp.json()[0]
    assert "code" in lang
    assert "name" in lang


def test_get_settings_returns_defaults(client):
    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "selected_voice_id" in data
    assert "default_language" in data


def test_get_settings_default_voice(client):
    resp = client.get("/settings")
    data = resp.json()
    assert data["selected_voice_id"] == "sarvam:ishita"


def test_get_settings_default_language(client):
    resp = client.get("/settings")
    data = resp.json()
    assert data["default_language"] == "en-IN"


def test_update_settings_persists(client):
    resp = client.post("/settings", json={"selected_voice_id": "nova"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["selected_voice_id"] == "nova"


def test_update_settings_custom_key(client):
    resp = client.post("/settings", json={"agent_name": "TestBot"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_name"] == "TestBot"


def test_update_settings_overwrites_existing(client):
    client.post("/settings", json={"default_language": "hi-IN"})
    resp = client.post("/settings", json={"default_language": "te-IN"})
    assert resp.status_code == 200
    assert resp.json()["default_language"] == "te-IN"
