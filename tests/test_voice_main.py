"""Tests for voice_agent/main.py utility functions."""
import sys
import os
import importlib.util
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# conftest.py already stubs livekit.agents

# Stub livekit.plugins before import
_lk_plugins = MagicMock()
sys.modules.setdefault('livekit.plugins', _lk_plugins)
sys.modules.setdefault('livekit.plugins.deepgram', MagicMock())
sys.modules.setdefault('livekit.plugins.elevenlabs', MagicMock())
sys.modules.setdefault('livekit.plugins.openai', MagicMock())
sys.modules.setdefault('livekit.plugins.silero', MagicMock())

# AgentSession must be importable
import livekit.agents as _lk_agents
_lk_agents.AgentSession = MagicMock()
_lk_agents.JobContext = MagicMock()
_lk_agents.WorkerOptions = MagicMock()
_lk_agents.cli = MagicMock()
_lk_agents.tts.StreamAdapter = MagicMock()
_lk_agents.stt.StreamAdapter = MagicMock()

# Stub hybrid_tts module (already tested separately)
sys.modules.setdefault('hybrid_tts', MagicMock())

# Load voice_agent/main.py with a unique module name to avoid colliding with api/main.py
_VOICE_MAIN_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent', 'main.py')
_VOICE_MAIN_PATH = os.path.normpath(_VOICE_MAIN_PATH)

if 'voice_agent_main' not in sys.modules:
    # Temporarily add voice_agent to sys.path for relative imports inside main.py
    _va_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))
    _spec = importlib.util.spec_from_file_location("voice_agent_main", _VOICE_MAIN_PATH,
                                                    submodule_search_locations=[_va_path])
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules['voice_agent_main'] = _mod
    # Make voice_agent modules resolvable during exec
    if _va_path not in sys.path:
        sys.path.insert(0, _va_path)
    _spec.loader.exec_module(_mod)

voice_main = sys.modules['voice_agent_main']


# ── fetch_settings ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_fetch_settings_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"agent_name": "Aira"}
    voice_main._api_client.get = AsyncMock(return_value=mock_resp)
    result = await voice_main.fetch_settings()
    assert result["agent_name"] == "Aira"


@pytest.mark.asyncio
async def test_fetch_settings_non_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    voice_main._api_client.get = AsyncMock(return_value=mock_resp)
    result = await voice_main.fetch_settings()
    assert result == {}


@pytest.mark.asyncio
async def test_fetch_settings_exception():
    voice_main._api_client.get = AsyncMock(side_effect=Exception("Network error"))
    result = await voice_main.fetch_settings()
    assert result == {}


# ── _save_transcript ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_transcript_success():
    voice_main._api_client.post = AsyncMock()
    await voice_main._save_transcript("sess-1", "user", "Hello")
    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_transcript_exception():
    voice_main._api_client.post = AsyncMock(side_effect=Exception("Network"))
    await voice_main._save_transcript("sess-2", "agent", "Hi")  # should not raise


# ── _save_metrics ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_metrics_provider_only():
    voice_main._api_client.post = AsyncMock()
    mock_metrics_module = MagicMock()
    mock_metrics_module.LLMMetrics = type("LLMMetrics", (), {})
    mock_metrics_module.TTSMetrics = type("TTSMetrics", (), {})
    mock_metrics_module.STTMetrics = type("STTMetrics", (), {})
    with patch.dict(sys.modules, {'livekit.agents.metrics': mock_metrics_module}):
        await voice_main._save_metrics("sess-1", None, tts_provider="OpenAI")
    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_metrics_llm():
    voice_main._api_client.post = AsyncMock()

    # Create LLMMetrics-like object by making isinstance return True
    mock_metrics = MagicMock()
    mock_metrics.prompt_tokens = 10
    mock_metrics.completion_tokens = 5
    mock_metrics.ttft = 0.5

    # Patch the metric class lookup in livekit.agents.metrics
    mock_metrics_module = MagicMock()
    LLMMetrics = type("LLMMetrics", (), {})
    TTSMetrics = type("TTSMetrics", (), {})
    STTMetrics = type("STTMetrics", (), {})
    mock_metrics_module.LLMMetrics = LLMMetrics
    mock_metrics_module.TTSMetrics = TTSMetrics
    mock_metrics_module.STTMetrics = STTMetrics

    llm_instance = LLMMetrics()
    llm_instance.prompt_tokens = 10
    llm_instance.completion_tokens = 5
    llm_instance.ttft = 0.5

    with patch.dict(sys.modules, {'livekit.agents.metrics': mock_metrics_module}):
        await voice_main._save_metrics("sess-2", llm_instance)

    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_metrics_tts():
    voice_main._api_client.post = AsyncMock()

    mock_metrics_module = MagicMock()
    LLMMetrics = type("LLMMetrics", (), {})
    TTSMetrics = type("TTSMetrics", (), {})
    STTMetrics = type("STTMetrics", (), {})
    mock_metrics_module.LLMMetrics = LLMMetrics
    mock_metrics_module.TTSMetrics = TTSMetrics
    mock_metrics_module.STTMetrics = STTMetrics

    tts_instance = TTSMetrics()
    tts_instance.characters_count = 50
    tts_instance.ttfb = 0.3

    with patch.dict(sys.modules, {'livekit.agents.metrics': mock_metrics_module}):
        await voice_main._save_metrics("sess-3", tts_instance)

    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_metrics_stt():
    voice_main._api_client.post = AsyncMock()

    mock_metrics_module = MagicMock()
    LLMMetrics = type("LLMMetrics", (), {})
    TTSMetrics = type("TTSMetrics", (), {})
    STTMetrics = type("STTMetrics", (), {})
    mock_metrics_module.LLMMetrics = LLMMetrics
    mock_metrics_module.TTSMetrics = TTSMetrics
    mock_metrics_module.STTMetrics = STTMetrics

    stt_instance = STTMetrics()
    stt_instance.audio_duration = 2.5
    stt_instance.duration = 0.1

    with patch.dict(sys.modules, {'livekit.agents.metrics': mock_metrics_module}):
        await voice_main._save_metrics("sess-4", stt_instance)

    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_metrics_exception():
    voice_main._api_client.post = AsyncMock(side_effect=Exception("error"))
    mock_metrics_module = MagicMock()
    mock_metrics_module.LLMMetrics = type("LLMMetrics", (), {})
    mock_metrics_module.TTSMetrics = type("TTSMetrics", (), {})
    mock_metrics_module.STTMetrics = type("STTMetrics", (), {})
    with patch.dict(sys.modules, {'livekit.agents.metrics': mock_metrics_module}):
        await voice_main._save_metrics("sess-5", None, tts_provider="test")  # should not raise


# ── _resolve_caller_phone ─────────────────────────────────────────────────────
def test_resolve_caller_phone_none():
    result = voice_main._resolve_caller_phone(None)
    assert result == "+00 00000 00000"


def test_resolve_caller_phone_sip_with_plus():
    result = voice_main._resolve_caller_phone("sip:+919876543210@sip.provider.com")
    assert result == "+919876543210"


def test_resolve_caller_phone_sip_without_plus():
    result = voice_main._resolve_caller_phone("sip:919876543210@host")
    assert result == "+919876543210"


def test_resolve_caller_phone_e164():
    result = voice_main._resolve_caller_phone("+919876543210")
    assert result == "+919876543210"


def test_resolve_caller_phone_web():
    result = voice_main._resolve_caller_phone("web-user-12345")
    assert result == "+00 00000 00000"


def test_resolve_caller_phone_numeric():
    result = voice_main._resolve_caller_phone("1234567890")
    assert result == "1234567890"


# ── register_call ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_register_call_success():
    voice_main._api_client.post = AsyncMock()
    await voice_main.register_call("sess-1", "room-1", "+911234567890", "2024-01-01T00:00:00")
    voice_main._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_register_call_exception():
    voice_main._api_client.post = AsyncMock(side_effect=Exception("err"))
    await voice_main.register_call("sess-2", "room-2", None, "2024-01-01T00:00:00")  # should not raise


# ── _prewarm_tts ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_prewarm_tts_success():
    async def fake_synthesize(text):
        yield MagicMock()

    mock_tts = MagicMock()
    mock_tts.synthesize = fake_synthesize
    await voice_main._prewarm_tts(mock_tts)  # should not raise


@pytest.mark.asyncio
async def test_prewarm_tts_exception():
    async def fake_synthesize_error(text):
        raise Exception("TTS error")
        yield  # make it a generator

    mock_tts = MagicMock()
    mock_tts.synthesize = fake_synthesize_error
    await voice_main._prewarm_tts(mock_tts)  # should not raise (best-effort)


# ── _prewarm_sarvam ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_prewarm_sarvam_success():
    mock_http = AsyncMock()
    mock_sarvam_module = MagicMock()
    mock_sarvam_module._http_client = mock_http

    with patch.dict(sys.modules, {'sarvam_tts': mock_sarvam_module}):
        await voice_main._prewarm_sarvam("test-key")

    assert mock_http.post.call_count == 3  # one for each language


@pytest.mark.asyncio
async def test_prewarm_sarvam_exception():
    mock_http = AsyncMock()
    mock_http.post = AsyncMock(side_effect=Exception("timeout"))
    mock_sarvam_module = MagicMock()
    mock_sarvam_module._http_client = mock_http

    with patch.dict(sys.modules, {'sarvam_tts': mock_sarvam_module}):
        await voice_main._prewarm_sarvam("test-key")  # should not raise


# ── OPENAI_VOICES ─────────────────────────────────────────────────────────────
def test_openai_voices_set():
    assert "nova" in voice_main.OPENAI_VOICES
    assert "alloy" in voice_main.OPENAI_VOICES
    assert len(voice_main.OPENAI_VOICES) >= 5
