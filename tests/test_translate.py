"""Tests for translate.py route — mocking OpenAI to avoid real API calls."""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app():
    """Build a FastAPI app with translate router, no real OpenAI needed."""
    if 'routes.translate' in sys.modules:
        del sys.modules['routes.translate']
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
        from routes.translate import router
        app = FastAPI()
        app.include_router(router)
        return app


@pytest.fixture(scope="module")
def app():
    return _make_app()


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


def _mock_openai_response(translations):
    """Build a mock OpenAI response that returns the given translations list."""
    import json
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({"translations": translations})
    return mock_resp


def test_translate_empty_list(client):
    resp = client.post("/translate", json={"texts": []})
    assert resp.status_code == 200
    assert resp.json() == {"translations": []}


def test_translate_all_empty_strings(client):
    resp = client.post("/translate", json={"texts": ["", "  "]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["translations"] == ["", "  "]


def test_translate_english_passthrough(client):
    """English strings should still go through OpenAI but be returned unchanged."""
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(["hello"])
    )
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        resp = client.post("/translate", json={"texts": ["hello"]})
    assert resp.status_code == 200
    assert resp.json()["translations"] == ["hello"]


def test_translate_hindi_to_english(client):
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(["Hello"])
    )
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        resp = client.post("/translate", json={"texts": ["नमस्ते"]})
    assert resp.status_code == 200
    assert resp.json()["translations"] == ["Hello"]


def test_translate_multiple_strings(client):
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(["Hello", "How are you"])
    )
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        resp = client.post("/translate", json={"texts": ["नमस्ते", "कैसे हो"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["translations"] == ["Hello", "How are you"]


def test_translate_mixed_empty_and_non_empty(client):
    """Empty strings stay empty; only non-empty go through translation."""
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(
        return_value=_mock_openai_response(["Hello"])
    )
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        resp = client.post("/translate", json={"texts": ["", "नमस्ते"]})
    assert resp.status_code == 200
    data = resp.json()
    # first empty stays empty, second gets translated
    assert data["translations"][0] == ""
    assert data["translations"][1] == "Hello"


def test_translate_openai_failure_returns_originals(client):
    """On OpenAI error, graceful fallback returns originals unchanged."""
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        resp = client.post("/translate", json={"texts": ["नमस्ते", "how are you"]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["translations"] == ["नमस्ते", "how are you"]
