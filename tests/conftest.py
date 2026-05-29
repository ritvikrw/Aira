"""
Shared pytest configuration.
Stubs livekit before any test module is imported so all test files share
the same mock objects and there are no sys.modules conflicts.
"""
import sys
import os
from unittest.mock import MagicMock

# Add voice_agent to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

# ── Minimal livekit.agents.stt stubs ─────────────────────────────────────────
class FakeSTTCapabilities:
    def __init__(self, **kw): pass

class FakeSTTBase:
    def __init__(self, capabilities=None): pass

class FakeSpeechEventType:
    FINAL_TRANSCRIPT = "FINAL_TRANSCRIPT"

class FakeSpeechData:
    def __init__(self, text="", language="", confidence=1.0):
        self.text = text
        self.language = language
        self.confidence = confidence

class FakeSpeechEvent:
    def __init__(self, type, alternatives=None):
        self.type = type
        self.alternatives = alternatives or []

# ── Minimal livekit.agents.tts stubs ─────────────────────────────────────────
class FakeTTSCapabilities:
    def __init__(self, **kw): pass

class FakeTTSBase:
    def __init__(self, capabilities=None, sample_rate=22050, num_channels=1): pass

class FakeChunkedStream:
    def __init__(self, *, tts, input_text, conn_options): pass

# ── Build stubs ───────────────────────────────────────────────────────────────
lk_stt_mock = MagicMock(name="livekit.agents.stt")
lk_stt_mock.STT             = FakeSTTBase
lk_stt_mock.STTCapabilities = FakeSTTCapabilities
lk_stt_mock.SpeechEventType = FakeSpeechEventType
lk_stt_mock.SpeechData      = FakeSpeechData
lk_stt_mock.SpeechEvent     = FakeSpeechEvent

lk_tts_mock = MagicMock(name="livekit.agents.tts")
lk_tts_mock.TTS             = FakeTTSBase
lk_tts_mock.TTSCapabilities = FakeTTSCapabilities
lk_tts_mock.ChunkedStream   = FakeChunkedStream

lk_utils_mock = MagicMock(name="livekit.agents.utils")

lk_types_mock = MagicMock(name="livekit.agents.types")
lk_types_mock.DEFAULT_API_CONNECT_OPTIONS = object()
lk_types_mock.APIConnectOptions           = type("APIConnectOptions", (), {})
lk_types_mock.NotGivenOr                  = type("NotGivenOr",        (), {})
lk_types_mock.NOT_GIVEN                   = object()

# Parent mock — attributes must match what modules get via `from livekit.agents import X`
lk_agents_mock         = MagicMock(name="livekit.agents")
lk_agents_mock.stt     = lk_stt_mock
lk_agents_mock.tts     = lk_tts_mock
lk_agents_mock.utils   = lk_utils_mock
lk_agents_mock.types   = lk_types_mock

# Register everything (force-set, not setdefault, so this file always wins)
sys.modules["livekit"]              = MagicMock()
sys.modules["livekit.rtc"]          = MagicMock()
sys.modules["livekit.agents"]       = lk_agents_mock
sys.modules["livekit.agents.stt"]   = lk_stt_mock
sys.modules["livekit.agents.tts"]   = lk_tts_mock
sys.modules["livekit.agents.utils"] = lk_utils_mock
sys.modules["livekit.agents.types"] = lk_types_mock

# Expose so test files can import from conftest
__all__ = [
    "lk_utils_mock", "lk_stt_mock", "lk_tts_mock", "lk_agents_mock",
    "FakeSpeechEvent", "FakeSpeechData", "FakeSpeechEventType",
]
