"""Tests for voice_agent/hybrid_tts.py."""
import sys
import os
import struct
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py stubs livekit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))

# Stub sarvam_tts helpers used by hybrid_tts at module level
import sarvam_tts as _sarvam_tts_mod
_sarvam_detect = MagicMock(return_value=None)
_sarvam_wav = MagicMock(return_value=(b'\x00' * 100, 22050))

import hybrid_tts as _htts_mod

# Patch at module level
_htts_mod._detect_script_language = _sarvam_detect
_htts_mod._wav_to_pcm_with_rate = _sarvam_wav

from hybrid_tts import (
    _resample_to_24k, HybridTTS, _HybridChunkedStream,
    OPENAI_SAMPLE_RATE, SARVAM_SAMPLE_RATE, BEST_SPEAKERS,
)


# ── _resample_to_24k ──────────────────────────────────────────────────────────
def test_resample_already_24k():
    data = struct.pack("<4h", 100, 200, 300, 400)
    result = _resample_to_24k(data, OPENAI_SAMPLE_RATE)
    assert result == data


def test_resample_empty():
    result = _resample_to_24k(b"", 22050)
    assert result == b""


def test_resample_22050_to_24k():
    # Create 100 samples at 22050 Hz
    samples = [i * 100 for i in range(100)]
    data = struct.pack(f"<{len(samples)}h", *samples)
    result = _resample_to_24k(data, 22050)
    # Output should have more samples (upsampled)
    n_out = len(result) // 2
    assert n_out > 90  # roughly len * (24000/22050)


def test_resample_clips_values():
    # max value should stay within int16 range
    data = struct.pack("<2h", 32767, 32767)
    result = _resample_to_24k(data, 22050)
    samples = struct.unpack(f"<{len(result)//2}h", result)
    assert all(-32768 <= s <= 32767 for s in samples)


def test_resample_single_sample():
    data = struct.pack("<1h", 1000)
    result = _resample_to_24k(data, 22050)
    assert len(result) >= 2  # at least 1 output sample


# ── HybridTTS ────────────────────────────────────────────────────────────────
def test_hybrid_tts_init():
    tts = HybridTTS(sarvam_api_key="test-key")
    assert tts._sarvam_key == "test-key"
    assert tts._openai_key == ""
    assert tts._eleven_key == ""
    assert tts._openai_voice == "nova"


def test_hybrid_tts_model_property():
    tts = HybridTTS(sarvam_api_key="key")
    assert tts.model == "hybrid"


def test_hybrid_tts_provider_property():
    tts = HybridTTS(sarvam_api_key="key")
    assert tts.provider == "hybrid"


def test_hybrid_tts_synthesize_returns_stream():
    tts = HybridTTS(sarvam_api_key="key")
    stream = tts.synthesize("Hello world")
    assert isinstance(stream, _HybridChunkedStream)


def test_best_speakers_contains_languages():
    assert "hi-IN" in BEST_SPEAKERS
    assert "te-IN" in BEST_SPEAKERS
    assert "ta-IN" in BEST_SPEAKERS
    assert "en-IN" in BEST_SPEAKERS


# ── _HybridChunkedStream._run ─────────────────────────────────────────────────
def _make_stream(sarvam_key="sk", openai_key="", eleven_key="", eleven_voice="",
                 text="Hello", speaker_explicit=False):
    tts_obj = HybridTTS(
        sarvam_api_key=sarvam_key,
        openai_api_key=openai_key,
        eleven_api_key=eleven_key,
        eleven_voice_id=eleven_voice,
        sarvam_speaker_explicit=speaker_explicit,
    )
    stream = _HybridChunkedStream(
        tts=tts_obj,
        input_text=text,
        conn_options=MagicMock(),
        sarvam_key=sarvam_key,
        sarvam_speaker="ishita",
        sarvam_speaker_explicit=speaker_explicit,
        sarvam_model="bulbul:v3",
        openai_key=openai_key,
        openai_voice="nova",
        eleven_key=eleven_key,
        eleven_voice=eleven_voice,
        eleven_model="eleven_turbo_v2_5",
    )
    return stream


@pytest.mark.asyncio
async def test_run_empty_text():
    stream = _make_stream(text="")
    emitter = MagicMock()
    await stream._run(emitter)
    emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_whitespace_text():
    stream = _make_stream(text="   ")
    emitter = MagicMock()
    await stream._run(emitter)
    emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_routes_to_sarvam():
    """Indian script detected → routes to Sarvam."""
    stream = _make_stream(sarvam_key="sk", text="नमस्ते")
    emitter = MagicMock()

    with patch.object(_htts_mod, '_detect_script_language', return_value="hi-IN"), \
         patch.object(stream, '_run_sarvam', AsyncMock()) as mock_sarvam:
        await stream._run(emitter)
    mock_sarvam.assert_called_once()


@pytest.mark.asyncio
async def test_run_routes_to_openai_english():
    """No script detected, openai key set → OpenAI."""
    stream = _make_stream(sarvam_key="sk", openai_key="oai-key", text="Hello world")
    emitter = MagicMock()

    with patch.object(_htts_mod, '_detect_script_language', return_value=None), \
         patch.object(stream, '_run_openai', AsyncMock()) as mock_oai:
        await stream._run(emitter)
    mock_oai.assert_called_once()


@pytest.mark.asyncio
async def test_run_routes_to_elevenlabs():
    """No script, eleven key set (no openai) → ElevenLabs."""
    stream = _make_stream(sarvam_key="sk", openai_key="", eleven_key="el-key",
                          eleven_voice="voice-id", text="Hello world")
    emitter = MagicMock()

    with patch.object(_htts_mod, '_detect_script_language', return_value=None), \
         patch.object(stream, '_run_elevenlabs', AsyncMock()) as mock_el:
        await stream._run(emitter)
    mock_el.assert_called_once()


@pytest.mark.asyncio
async def test_run_no_provider_warning():
    """No keys → just logs warning."""
    stream = _make_stream(sarvam_key="", openai_key="", eleven_key="", text="Hello")
    emitter = MagicMock()
    with patch.object(_htts_mod, '_detect_script_language', return_value=None):
        await stream._run(emitter)  # should not raise


@pytest.mark.asyncio
async def test_run_sarvam_with_pcm():
    stream = _make_stream(sarvam_key="sk", text="नमस्ते")
    emitter = MagicMock()

    # Fake PCM data (must be even number of bytes for int16 struct)
    fake_pcm = b'\x00\x01' * 50  # 100 bytes = 50 int16 samples

    with patch.object(stream, '_fetch_sarvam_pcm_24k', AsyncMock(return_value=fake_pcm)):
        await stream._run_sarvam(emitter, "नमस्ते", "hi-IN")

    emitter.initialize.assert_called_once()
    emitter.push.assert_called_once_with(fake_pcm)
    emitter.end_input.assert_called_once()


@pytest.mark.asyncio
async def test_run_sarvam_empty_pcm():
    stream = _make_stream(sarvam_key="sk", text="test")
    emitter = MagicMock()

    with patch.object(stream, '_fetch_sarvam_pcm_24k', AsyncMock(return_value=b"")):
        await stream._run_sarvam(emitter, "test", "hi-IN")

    emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_sarvam_explicit_speaker():
    """With speaker_explicit=True, use the configured speaker."""
    stream = _make_stream(sarvam_key="sk", text="test", speaker_explicit=True)
    emitter = MagicMock()

    with patch.object(stream, '_fetch_sarvam_pcm_24k', AsyncMock(return_value=b"")):
        await stream._run_sarvam(emitter, "test", "hi-IN")
    # No error, function just returns early due to empty pcm


@pytest.mark.asyncio
async def test_fetch_sarvam_pcm_success():
    stream = _make_stream(sarvam_key="sk")

    fake_wav = b"RIFF" + b"\x00" * 40 + b"\x00\x01" * 100
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": ["AAAA"]}  # base64 "AAAA" = b'\x00\x00\x00'

    with patch.object(_htts_mod, '_wav_to_pcm_with_rate', return_value=(b'\x00' * 100, 22050)), \
         patch.object(_htts_mod._http_client, 'post', AsyncMock(return_value=mock_resp)):
        result = await stream._fetch_sarvam_pcm_24k("Hello", "hi-IN", "ishita")
    # Result is resampled, non-empty since input was non-empty
    assert isinstance(result, bytes)


@pytest.mark.asyncio
async def test_fetch_sarvam_pcm_empty_audio():
    stream = _make_stream(sarvam_key="sk")
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [""]}

    with patch.object(_htts_mod._http_client, 'post', AsyncMock(return_value=mock_resp)):
        result = await stream._fetch_sarvam_pcm_24k("Hello", "hi-IN", "ishita")
    assert result == b""


@pytest.mark.asyncio
async def test_run_openai_success():
    stream = _make_stream(openai_key="oai-key")
    emitter = MagicMock()

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.aiter_bytes = MagicMock(return_value=_async_gen([b"pcm-data"]))

    with patch.object(_htts_mod._http_client, 'stream', return_value=mock_resp):
        await stream._run_openai(emitter, "Hello world")

    emitter.initialize.assert_called_once()
    emitter.end_input.assert_called_once()


@pytest.mark.asyncio
async def test_run_openai_http_error():
    stream = _make_stream(openai_key="oai-key")
    emitter = MagicMock()

    mock_resp = AsyncMock()
    mock_resp.status_code = 401
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    mock_resp.aiter_bytes = MagicMock(return_value=_async_gen([]))

    with patch.object(_htts_mod._http_client, 'stream', return_value=mock_resp):
        await stream._run_openai(emitter, "Hello")

    emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_openai_exception():
    stream = _make_stream(openai_key="oai-key")
    emitter = MagicMock()

    with patch.object(_htts_mod._http_client, 'stream', side_effect=Exception("network")):
        await stream._run_openai(emitter, "Hello")  # should not raise


@pytest.mark.asyncio
async def test_run_elevenlabs_success():
    stream = _make_stream(eleven_key="el-key", eleven_voice="voice-id")
    emitter = MagicMock()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b"pcm-data"

    with patch.object(_htts_mod._http_client, 'post', AsyncMock(return_value=mock_resp)):
        await stream._run_elevenlabs(emitter, "Hello")

    emitter.initialize.assert_called_once()
    emitter.push.assert_called_once_with(b"pcm-data")
    emitter.end_input.assert_called_once()


@pytest.mark.asyncio
async def test_run_elevenlabs_empty_response():
    stream = _make_stream(eleven_key="el-key", eleven_voice="voice-id")
    emitter = MagicMock()

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.content = b""

    with patch.object(_htts_mod._http_client, 'post', AsyncMock(return_value=mock_resp)):
        await stream._run_elevenlabs(emitter, "Hello")

    emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_elevenlabs_exception():
    stream = _make_stream(eleven_key="el-key", eleven_voice="voice-id")
    emitter = MagicMock()

    with patch.object(_htts_mod._http_client, 'post', AsyncMock(side_effect=Exception("err"))):
        await stream._run_elevenlabs(emitter, "Hello")  # should not raise

    emitter.initialize.assert_not_called()


# ── helper ────────────────────────────────────────────────────────────────────
async def _async_gen_impl(items):
    for item in items:
        yield item

def _async_gen(items):
    return _async_gen_impl(items)
