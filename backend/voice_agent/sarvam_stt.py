"""
Sarvam AI STT — saarika:v2.5.

Language handling:
- First utterance (language selection): forced en-IN so "Telugu"/"Hindi"/… comes
  out as clean English text regardless of how the caller pronounces it.
- After lock: always pass the locked language_code — the "Telugu executive" handles
  everything from here on.
- Lock is set by agent.py after language is confirmed.
- Lock can only be changed by explicit text-based switch detection in agent.py.
"""

from __future__ import annotations

import asyncio
import io
import time
import wave
import logging
import os

import httpx
from livekit.agents import stt, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, NotGivenOr, NOT_GIVEN

logger = logging.getLogger(__name__)

# Last measured Sarvam API round-trip latency in ms — read by main.py _save_metrics
last_stt_latency_ms: float | None = None

detected_language: str = "en-IN"
_locked_language:  str = ""       # Set after language confirmed — passed to Sarvam for accuracy

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
_http_client = httpx.AsyncClient(timeout=30.0)


def lock_language(lang: str) -> None:
    """Lock the session language. STT will pass this to Sarvam on every subsequent call."""
    global detected_language, _locked_language
    if lang and lang != "unknown":
        detected_language = lang
        _locked_language  = lang
        logger.info("Language locked: %s", lang)


def reset_language() -> None:
    """Reset at start of new call."""
    global detected_language, _locked_language
    detected_language = "en-IN"
    _locked_language  = ""


class SarvamSTT(stt.STT):
    def __init__(self, *, api_key: str | None = None, language: str = "unknown", model: str = "saarika:v2.5"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._api_key  = api_key or os.getenv("SARVAM_API_KEY", "")
        self._language = language
        self._model    = model

    @property
    def model(self) -> str: return self._model

    @property
    def provider(self) -> str: return "sarvam"

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        global detected_language

        # After language is locked, pass it to Sarvam explicitly for better accuracy.
        # Before lock (language-selection turn), force English so the user's one-word
        # answer ("Telugu", "Hindi", …) is transcribed cleanly in English script
        # instead of being auto-detected as the wrong Indian language.
        if _locked_language:
            lang = _locked_language
        else:
            lang = "unknown"  # auto-detect — lets Sarvam hear "Telugu" correctly instead of "There you go"

        audio_bytes = _frames_to_wav(buffer)
        form: dict[str, str] = {"model": self._model}
        if lang and lang != "unknown":
            form["language_code"] = lang

        global last_stt_latency_ms
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                _t0 = time.perf_counter()
                resp = await _http_client.post(
                    SARVAM_STT_URL,
                    headers={"api-subscription-key": self._api_key},
                    files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                    data=form,
                )
                last_stt_latency_ms = round((time.perf_counter() - _t0) * 1000, 1)
                resp.raise_for_status()
                data = resp.json()
                last_exc = None
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 503 and attempt < 2:
                    logger.warning("Sarvam STT 503, retrying (%d/3)…", attempt + 1)
                    await asyncio.sleep(0.3 * (attempt + 1))
                    last_exc = e
                    continue
                logger.error("Sarvam STT HTTP %s: %s", e.response.status_code, e.response.text)
                return _empty_event(detected_language)
            except Exception as e:
                logger.error("Sarvam STT error: %s", e)
                return _empty_event(detected_language)

        if last_exc:
            return _empty_event(detected_language)

        transcript    = (data.get("transcript") or "").strip()
        detected_lang = data.get("language_code") or lang or "en-IN"

        _SUPPORTED = {"en-IN", "hi-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN"}

        # Only update detected_language if not locked and language is supported
        if not _locked_language and detected_lang and detected_lang != "unknown":
            detected_language = detected_lang if detected_lang in _SUPPORTED else "en-IN"

        if not transcript:
            logger.warning("Sarvam STT empty result [%s%s] — audio too short or silence", detected_lang, " locked" if _locked_language else "")
        else:
            logger.info("Sarvam STT [%s%s]: %r", detected_lang, " locked" if _locked_language else "", transcript[:120])

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=transcript, language=detected_lang, confidence=1.0)],
        )


def _empty_event(lang: str) -> stt.SpeechEvent:
    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[stt.SpeechData(text="", language=lang, confidence=0.0)],
    )


def _frames_to_wav(buffer: utils.AudioBuffer) -> bytes:
    merged = utils.merge_frames(buffer)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(merged.num_channels)
        wf.setsampwidth(2)
        wf.setframerate(merged.sample_rate)
        wf.writeframes(merged.data.tobytes())
    return buf.getvalue()
