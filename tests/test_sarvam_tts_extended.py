"""Extended tests for sarvam_tts.py — covering the synthesis path."""
import io
import wave
import struct
import base64
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py stubs livekit
from conftest import lk_utils_mock

import sarvam_tts


def _make_wav_b64(sample_rate=22050, num_frames=100):
    """Create a base64-encoded WAV file for mocking API responses."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack('<' + 'h' * num_frames, *([1000] * num_frames)))
    return base64.b64encode(buf.getvalue()).decode()


# ── SarvamTTS class ───────────────────────────────────────────────────────────
def test_sarvam_tts_model_property():
    tts = sarvam_tts.SarvamTTS(api_key="k", model="bulbul:v3")
    assert tts.model == "bulbul:v3"


def test_sarvam_tts_provider_property():
    tts = sarvam_tts.SarvamTTS(api_key="k")
    assert tts.provider == "sarvam"


def test_sarvam_tts_synthesize_returns_stream():
    tts_obj = sarvam_tts.SarvamTTS(api_key="k")
    stream = tts_obj.synthesize("hello")
    assert isinstance(stream, sarvam_tts._SarvamChunkedStream)


def test_sarvam_tts_default_speaker():
    tts = sarvam_tts.SarvamTTS(api_key="k")
    assert tts._speaker == "ishita"


def test_sarvam_tts_custom_speaker():
    tts = sarvam_tts.SarvamTTS(api_key="k", speaker="priya")
    assert tts._speaker == "priya"


# ── _SarvamChunkedStream._run ─────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_run_english_text():
    """English text should use stt detected_language fallback."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [_make_wav_b64()]}
    sarvam_tts._http_client.post = AsyncMock(return_value=mock_resp)

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="Hello, how can I help you?",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    mock_emitter.initialize = MagicMock()
    mock_emitter.push = MagicMock()
    mock_emitter.end_input = MagicMock()

    await stream._run(mock_emitter)

    mock_emitter.initialize.assert_called_once()
    mock_emitter.push.assert_called_once()
    mock_emitter.end_input.assert_called_once()


@pytest.mark.asyncio
async def test_run_telugu_text():
    """Telugu text should detect te-IN from script."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [_make_wav_b64()]}
    sarvam_tts._http_client.post = AsyncMock(return_value=mock_resp)

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="నమస్కారం",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    mock_emitter.initialize = MagicMock()
    mock_emitter.push = MagicMock()
    mock_emitter.end_input = MagicMock()

    await stream._run(mock_emitter)
    # Telugu script should trigger te-IN language detection
    call_kwargs = sarvam_tts._http_client.post.call_args[1]["json"]
    assert call_kwargs["target_language_code"] == "te-IN"


@pytest.mark.asyncio
async def test_run_empty_audio_response():
    """Empty audio response from API should not call emitter."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [""]}
    sarvam_tts._http_client.post = AsyncMock(return_value=mock_resp)

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="hello",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    await stream._run(mock_emitter)
    mock_emitter.initialize.assert_not_called()


@pytest.mark.asyncio
async def test_run_http_timeout_retries():
    """Timeout on first attempt should retry."""
    import httpx
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [_make_wav_b64()]}

    sarvam_tts._http_client.post = AsyncMock(side_effect=[
        httpx.ReadTimeout("timeout"),
        mock_resp,
    ])

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="Hello",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    mock_emitter.initialize = MagicMock()
    mock_emitter.push = MagicMock()
    mock_emitter.end_input = MagicMock()

    await stream._run(mock_emitter)
    assert sarvam_tts._http_client.post.call_count == 2


@pytest.mark.asyncio
async def test_run_503_retries():
    """503 on first attempt should retry."""
    import httpx
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.text = "Service Unavailable"
    err = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_503)

    mock_ok = MagicMock()
    mock_ok.raise_for_status = MagicMock()
    mock_ok.json.return_value = {"audios": [_make_wav_b64()]}

    sarvam_tts._http_client.post = AsyncMock(side_effect=[err, mock_ok])

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="Hello",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    mock_emitter.initialize = MagicMock()
    mock_emitter.push = MagicMock()
    mock_emitter.end_input = MagicMock()

    await stream._run(mock_emitter)
    assert sarvam_tts._http_client.post.call_count == 2


@pytest.mark.asyncio
async def test_run_non_503_http_error_no_retry():
    """Non-503 HTTP errors should not retry."""
    import httpx
    mock_400 = MagicMock()
    mock_400.status_code = 400
    mock_400.text = "Bad Request"
    err = httpx.HTTPStatusError("400", request=MagicMock(), response=mock_400)
    sarvam_tts._http_client.post = AsyncMock(side_effect=err)

    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text="Hello",
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    await stream._run(mock_emitter)
    # Should only try once (no retry on 400)
    assert sarvam_tts._http_client.post.call_count == 1


@pytest.mark.asyncio
async def test_run_long_text_chunks():
    """Text over 500 chars should be chunked."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"audios": [_make_wav_b64()]}
    sarvam_tts._http_client.post = AsyncMock(return_value=mock_resp)

    long_text = "Hello world " * 50  # 600 chars
    tts_obj = sarvam_tts.SarvamTTS(api_key="test-key")
    stream = sarvam_tts._SarvamChunkedStream(
        tts=tts_obj,
        input_text=long_text,
        conn_options=MagicMock(),
        api_key="test-key",
        speaker="ishita",
        model="bulbul:v3",
        pace=1.0,
    )

    mock_emitter = MagicMock()
    mock_emitter.initialize = MagicMock()
    mock_emitter.push = MagicMock()
    mock_emitter.end_input = MagicMock()

    await stream._run(mock_emitter)
    # Should have made 2 API calls (600 chars / 500 = 2 chunks)
    assert sarvam_tts._http_client.post.call_count == 2


# ── LANGUAGE_SPEAKERS ─────────────────────────────────────────────────────────
def test_language_speakers_has_english():
    assert "en-IN" in sarvam_tts.LANGUAGE_SPEAKERS


def test_language_speakers_has_telugu():
    assert "te-IN" in sarvam_tts.LANGUAGE_SPEAKERS


# ── _wav_to_pcm (legacy) ──────────────────────────────────────────────────────
def test_wav_to_pcm_legacy():
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(22050)
        wf.writeframes(struct.pack('<hh', 100, 200))
    pcm = sarvam_tts._wav_to_pcm(buf.getvalue())
    assert isinstance(pcm, bytes)
    assert len(pcm) == 4  # 2 frames × 2 bytes
