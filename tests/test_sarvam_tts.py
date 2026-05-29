"""
Tests for utility functions in sarvam_tts.py.
"""
import sys
import os
import io
import wave
import struct
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))


def test_detect_script_language_latin():
    """_detect_script_language("hello") returns None for Latin text."""
    from sarvam_tts import _detect_script_language
    assert _detect_script_language("hello") is None


def test_detect_script_language_telugu():
    """_detect_script_language detects Telugu script."""
    from sarvam_tts import _detect_script_language
    assert _detect_script_language("నమస్కారం") == "te-IN"


def test_detect_script_language_hindi():
    """_detect_script_language detects Hindi/Devanagari script."""
    from sarvam_tts import _detect_script_language
    assert _detect_script_language("नमस्ते") == "hi-IN"


def test_detect_script_language_devanagari():
    """_detect_script_language detects Devanagari (Hindi)."""
    from sarvam_tts import _detect_script_language
    result = _detect_script_language("नमस्ते")
    assert result == "hi-IN"


def test_detect_script_language_tamil():
    """_detect_script_language detects Tamil script."""
    from sarvam_tts import _detect_script_language
    assert _detect_script_language("வணக்கம்") == "ta-IN"


def test_detect_script_language_empty():
    """_detect_script_language returns None for empty string."""
    from sarvam_tts import _detect_script_language
    assert _detect_script_language("") is None


def _make_wav_bytes(sample_rate=22050, num_channels=1, num_frames=100):
    """Create a minimal valid WAV file in memory."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        # Write silence (zeros)
        data = struct.pack('<' + 'h' * num_frames, *([0] * num_frames))
        wf.writeframes(data)
    return buf.getvalue()


def test_wav_to_pcm_with_rate_returns_tuple():
    """_wav_to_pcm_with_rate with real WAV bytes returns (bytes, int)."""
    from sarvam_tts import _wav_to_pcm_with_rate
    wav_bytes = _make_wav_bytes(sample_rate=22050, num_frames=200)
    result = _wav_to_pcm_with_rate(wav_bytes)
    assert isinstance(result, tuple)
    assert len(result) == 2
    pcm_bytes, sample_rate = result
    assert isinstance(pcm_bytes, bytes)
    assert isinstance(sample_rate, int)
    assert sample_rate == 22050
    # 200 frames * 2 bytes (16-bit) = 400 bytes of PCM
    assert len(pcm_bytes) == 400


def test_wav_to_pcm_with_rate_different_sample_rate():
    """_wav_to_pcm_with_rate returns correct sample rate for 16000 Hz WAV."""
    from sarvam_tts import _wav_to_pcm_with_rate
    wav_bytes = _make_wav_bytes(sample_rate=16000, num_frames=160)
    _, rate = _wav_to_pcm_with_rate(wav_bytes)
    assert rate == 16000
