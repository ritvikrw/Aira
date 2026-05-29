"""Tests for utility functions in sarvam_tts.py."""
import io, wave, struct
import sarvam_tts   # conftest.py stubs livekit before this import


def _wav(sample_rate=22050, num_channels=1, num_frames=100):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack('<' + 'h' * num_frames, *([0] * num_frames)))
    return buf.getvalue()


def test_detect_script_language_latin():
    assert sarvam_tts._detect_script_language("hello") is None

def test_detect_script_language_telugu():
    assert sarvam_tts._detect_script_language("నమస్కారం") == "te-IN"

def test_detect_script_language_hindi():
    assert sarvam_tts._detect_script_language("नमस्ते") == "hi-IN"

def test_detect_script_language_devanagari():
    assert sarvam_tts._detect_script_language("नमस्कार") == "hi-IN"

def test_detect_script_language_tamil():
    assert sarvam_tts._detect_script_language("வணக்கம்") == "ta-IN"

def test_detect_script_language_empty():
    assert sarvam_tts._detect_script_language("") is None

def test_wav_to_pcm_with_rate_returns_tuple():
    pcm, rate = sarvam_tts._wav_to_pcm_with_rate(_wav(22050, num_frames=200))
    assert isinstance(pcm, bytes) and isinstance(rate, int)
    assert rate == 22050
    assert len(pcm) == 400   # 200 frames × 2 bytes

def test_wav_to_pcm_with_rate_sample_rate():
    _, rate = sarvam_tts._wav_to_pcm_with_rate(_wav(16000, num_frames=160))
    assert rate == 16000
