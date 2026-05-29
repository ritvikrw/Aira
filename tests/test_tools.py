"""Tests for voice_agent/tools.py — _persist_caller_name and search_knowledge_base."""
import sys
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py stubs livekit with function_tool as a pass-through
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))

import tools


# ── _persist_caller_name ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_persist_caller_name_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    tools._api_client.patch = AsyncMock(return_value=mock_resp)

    # Should not raise
    await tools._persist_caller_name("sess-123", "John Doe")
    tools._api_client.patch.assert_called_once()
    call_args = tools._api_client.patch.call_args
    assert "sess-123" in call_args[0][0]
    assert call_args[1]["json"]["caller_name"] == "John Doe"


@pytest.mark.asyncio
async def test_persist_caller_name_failure_does_not_raise():
    tools._api_client.patch = AsyncMock(side_effect=Exception("Network error"))
    # Should silently handle the error
    await tools._persist_caller_name("sess-err", "Jane")


# ── LANG_TO_SHORT map ────────────────────────────────────────────────────────
def test_lang_to_short_contains_telugu():
    assert tools._LANG_TO_SHORT["te-IN"] == "te"


def test_lang_to_short_contains_english():
    assert tools._LANG_TO_SHORT["en-IN"] == "en"


def test_lang_to_short_contains_hindi():
    assert tools._LANG_TO_SHORT["hi-IN"] == "hi"


# ── search_knowledge_base ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_knowledge_base_returns_results():
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"documents": ["doc1 content", "doc2 content"]}
    tools._api_client.post = AsyncMock(return_value=mock_resp)

    ctx = MagicMock()
    result = await tools.search_knowledge_base(ctx, "What are your services?")
    assert "doc1 content" in result
    assert "doc2 content" in result


@pytest.mark.asyncio
async def test_search_knowledge_base_empty_docs_tries_fallbacks():
    """When language-specific search returns empty, should try English fallback."""
    mock_resp_empty = MagicMock()
    mock_resp_empty.raise_for_status = MagicMock()
    mock_resp_empty.json.return_value = {"documents": []}

    mock_resp_en = MagicMock()
    mock_resp_en.raise_for_status = MagicMock()
    mock_resp_en.json.return_value = {"documents": ["english doc"]}

    tools._api_client.post = AsyncMock(side_effect=[mock_resp_empty, mock_resp_en])

    # Set detected language to something non-English
    with patch('sarvam_stt.detected_language', "te-IN"):
        ctx = MagicMock()
        result = await tools.search_knowledge_base(ctx, "query")
    assert "english doc" in result


@pytest.mark.asyncio
async def test_search_knowledge_base_all_empty_returns_fallback_message():
    """When all searches return empty docs, should return the fallback message."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"documents": []}
    tools._api_client.post = AsyncMock(return_value=mock_resp)

    ctx = MagicMock()
    result = await tools.search_knowledge_base(ctx, "unknown query")
    assert "No relevant information" in result


@pytest.mark.asyncio
async def test_search_knowledge_base_http_error_continues():
    """HTTP errors on individual payloads should be caught and continue."""
    import httpx
    mock_err = httpx.HTTPStatusError("404", request=MagicMock(), response=MagicMock())
    mock_ok = MagicMock()
    mock_ok.raise_for_status = MagicMock()
    mock_ok.json.return_value = {"documents": ["fallback result"]}
    tools._api_client.post = AsyncMock(side_effect=[mock_err, mock_ok])

    ctx = MagicMock()
    result = await tools.search_knowledge_base(ctx, "query")
    assert "fallback result" in result


@pytest.mark.asyncio
async def test_search_knowledge_base_network_failure_returns_message():
    """Total network failure should return the unavailable message."""
    tools._api_client.post = AsyncMock(side_effect=Exception("Connection refused"))

    ctx = MagicMock()
    result = await tools.search_knowledge_base(ctx, "query")
    assert "unavailable" in result.lower() or "No relevant" in result
