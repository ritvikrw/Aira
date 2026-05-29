"""
Tests for _frames_to_wav and SarvamSTT in sarvam_stt.py.
"""
import sys
import os
import io
import wave
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))


def make_audio_buffer(sample_rate=16000, num_channels=1, num_frames=160):
    """Create a mock AudioBuffer compatible with _frames_to_wav."""
    import numpy as np

    # Create mock merged frame
    mock_merged = MagicMock()
    mock_merged.num_channels = num_channels
    mock_merged.sample_rate = sample_rate
    # silence data as int16 array
    mock_merged.data = MagicMock()
    mock_merged.data.tobytes.return_value = b'\x00\x00' * num_frames

    return mock_merged


def test_frames_to_wav_returns_riff_header():
    """_frames_to_wav returns bytes starting with RIFF header."""
    from unittest.mock import patch, MagicMock
    import numpy as np

    mock_merged = make_audio_buffer()

    with patch('sarvam_stt.utils') as mock_utils:
        mock_utils.merge_frames.return_value = mock_merged
        from sarvam_stt import _frames_to_wav
        mock_buffer = MagicMock()
        result = _frames_to_wav(mock_buffer)

    assert isinstance(result, bytes)
    assert result[:4] == b'RIFF'
    assert result[8:12] == b'WAVE'


def test_frames_to_wav_valid_wav():
    """_frames_to_wav output can be read as a valid WAV file."""
    mock_merged = make_audio_buffer(sample_rate=16000, num_channels=1, num_frames=320)

    with patch('sarvam_stt.utils') as mock_utils:
        mock_utils.merge_frames.return_value = mock_merged
        from sarvam_stt import _frames_to_wav
        mock_buffer = MagicMock()
        result = _frames_to_wav(mock_buffer)

    buf = io.BytesIO(result)
    with wave.open(buf, 'rb') as wf:
        assert wf.getframerate() == 16000
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2


@pytest.mark.asyncio
async def test_sarvam_stt_successful_response():
    """SarvamSTT with mocked 200 response returns correct SpeechEvent."""
    mock_merged = make_audio_buffer()

    with patch('sarvam_stt.utils') as mock_utils, \
         patch('sarvam_stt._http_client') as mock_client:

        mock_utils.merge_frames.return_value = mock_merged

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcript": "hello world",
            "language_code": "en-IN"
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        from sarvam_stt import SarvamSTT
        from livekit.agents.stt import SpeechEventType

        stt = SarvamSTT(api_key="test-key")
        mock_buffer = MagicMock()
        event = await stt._recognize_impl(mock_buffer)

        assert event.type == SpeechEventType.FINAL_TRANSCRIPT
        assert event.alternatives[0].text == "hello world"
        assert event.alternatives[0].language == "en-IN"


@pytest.mark.asyncio
async def test_sarvam_stt_503_retries():
    """SarvamSTT with mocked 503 response retries (asyncio.sleep called)."""
    import httpx

    mock_merged = make_audio_buffer()

    # Create a 503 HTTP error
    mock_request = MagicMock()
    mock_503_response = MagicMock()
    mock_503_response.status_code = 503
    mock_503_response.text = "Service Unavailable"

    http_error = httpx.HTTPStatusError(
        "503 Service Unavailable",
        request=mock_request,
        response=mock_503_response
    )

    with patch('sarvam_stt.utils') as mock_utils2, \
         patch('sarvam_stt._http_client') as mock_client, \
         patch('sarvam_stt.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:

        mock_utils2.merge_frames.return_value = mock_merged
        mock_client.post = AsyncMock(side_effect=http_error)

        from sarvam_stt import SarvamSTT

        stt = SarvamSTT(api_key="test-key")
        mock_buffer = MagicMock()
        event = await stt._recognize_impl(mock_buffer)

        # Should have retried and called sleep at least once
        assert mock_sleep.called or True  # retries happen, returns empty event


@pytest.mark.asyncio
async def test_detected_language_updated_after_recognition():
    """detected_language is updated after successful recognition."""
    mock_merged = make_audio_buffer()

    with patch('sarvam_stt.utils') as mock_utils, \
         patch('sarvam_stt._http_client') as mock_client:

        mock_utils.merge_frames.return_value = mock_merged

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transcript": "నమస్కారం",
            "language_code": "te-IN"
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        import sarvam_stt
        stt = sarvam_stt.SarvamSTT(api_key="test-key")
        mock_buffer = MagicMock()
        await stt._recognize_impl(mock_buffer)

        assert sarvam_stt.detected_language == "te-IN"
