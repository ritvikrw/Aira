"""Tests for _frames_to_wav and SarvamSTT in sarvam_stt.py."""
import io, wave, asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# conftest.py stubs livekit — import shared mocks from it
from conftest import lk_utils_mock, FakeSpeechEventType

import sarvam_stt


def _merged(sample_rate=16000, num_channels=1, num_frames=160):
    m = MagicMock()
    m.num_channels = num_channels   # must be real int for wave module
    m.sample_rate  = sample_rate
    m.data = MagicMock()
    m.data.tobytes.return_value = b'\x00\x00' * num_frames
    return m


# ── _frames_to_wav ────────────────────────────────────────────────────────────
def test_frames_to_wav_returns_riff_header():
    lk_utils_mock.merge_frames.return_value = _merged()
    result = sarvam_stt._frames_to_wav(MagicMock())
    assert result[:4] == b'RIFF'
    assert result[8:12] == b'WAVE'


def test_frames_to_wav_valid_wav():
    lk_utils_mock.merge_frames.return_value = _merged(16000, 1, 320)
    result = sarvam_stt._frames_to_wav(MagicMock())
    with wave.open(io.BytesIO(result), 'rb') as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


# ── SarvamSTT ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_sarvam_stt_successful_response():
    lk_utils_mock.merge_frames.return_value = _merged()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"transcript": "hello world", "language_code": "en-IN"}
    sarvam_stt._http_client.post = AsyncMock(return_value=mock_resp)

    event = await sarvam_stt.SarvamSTT(api_key="k")._recognize_impl(MagicMock())
    assert event.type == FakeSpeechEventType.FINAL_TRANSCRIPT
    assert event.alternatives[0].text == "hello world"
    assert event.alternatives[0].language == "en-IN"


@pytest.mark.asyncio
async def test_sarvam_stt_503_retries():
    import httpx
    lk_utils_mock.merge_frames.return_value = _merged()

    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.text = "Service Unavailable"
    err = httpx.HTTPStatusError("503", request=MagicMock(), response=mock_503)
    sarvam_stt._http_client.post = AsyncMock(side_effect=[err, err, err, err])

    sleep_calls = []
    orig = asyncio.sleep
    async def _fake(t): sleep_calls.append(t)
    sarvam_stt.asyncio.sleep = _fake
    try:
        event = await sarvam_stt.SarvamSTT(api_key="k")._recognize_impl(MagicMock())
    finally:
        sarvam_stt.asyncio.sleep = orig

    assert len(sleep_calls) >= 1
    assert event.alternatives[0].text == ""


@pytest.mark.asyncio
async def test_detected_language_updated():
    lk_utils_mock.merge_frames.return_value = _merged()
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"transcript": "నమస్కారం", "language_code": "te-IN"}
    sarvam_stt._http_client.post = AsyncMock(return_value=mock_resp)

    await sarvam_stt.SarvamSTT(api_key="k")._recognize_impl(MagicMock())
    assert sarvam_stt.detected_language == "te-IN"
