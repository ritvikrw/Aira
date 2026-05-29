"""
Sarvam AI STT plugin for LiveKit agents (saarika:v2.5).

Uses speech-to-text endpoint with language_code=unknown — Sarvam auto-detects
the Indian language and returns the transcript in that language (Telugu stays
Telugu, Hindi stays Hindi, etc.).  The LLM receives native-language text and
responds naturally in the same language — no translation or language tags needed.

detected_language is updated on every result so HybridTTS can route to the
correct Sarvam bulbul voice automatically.

Usage in main.py:
    from sarvam_stt import SarvamSTT
    from livekit.agents.stt import StreamAdapter

    stt = StreamAdapter(stt=SarvamSTT(api_key=SARVAM_API_KEY), vad=silero.VAD.load())
"""

from __future__ import annotations

import asyncio
import io
import wave
import logging
import os

import httpx
from livekit.agents import stt, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions, NotGivenOr, NOT_GIVEN

logger = logging.getLogger(__name__)

# Shared state — updated on every STT result so HybridTTS knows the caller's language
detected_language: str = "en-IN"

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
_http_client = httpx.AsyncClient(timeout=30.0)


class SarvamSTT(stt.STT):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        language: str = "unknown",   # 'unknown' = auto-detect (recommended)
        model: str = "saarika:v2.5",
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=False, interim_results=False)
        )
        self._api_key  = api_key or os.getenv("SARVAM_API_KEY", "")
        self._language = language
        self._model    = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "sarvam"

    async def _recognize_impl(
        self,
        buffer: utils.AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:
        global detected_language

        lang = language if language is not NOT_GIVEN else self._language
        audio_bytes = _frames_to_wav(buffer)

        form: dict[str, str] = {"model": self._model}
        if lang and lang != "unknown":
            form["language_code"] = lang
        # When lang == "unknown" we omit language_code — Sarvam auto-detects

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = await _http_client.post(
                    SARVAM_STT_URL,
                    headers={"api-subscription-key": self._api_key},
                    files={"file": ("audio.wav", audio_bytes, "audio/wav")},
                    data=form,
                )
                resp.raise_for_status()
                data = resp.json()
                last_exc = None
                break
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 503 and attempt < 2:
                    logger.warning("Sarvam STT 503 overloaded, retrying (%d/3)…", attempt + 1)
                    await asyncio.sleep(0.3 * (attempt + 1))
                    last_exc = e
                    continue
                logger.error("Sarvam STT HTTP %s: %s", status, e.response.text)
                return _empty_event(detected_language)
            except Exception as e:
                logger.error("Sarvam STT error: %s", e)
                return _empty_event(detected_language)

        if last_exc is not None:
            logger.error("Sarvam STT failed after 3 retries, returning empty transcript")
            return _empty_event(detected_language)

        transcript    = (data.get("transcript") or "").strip()
        detected_lang = data.get("language_code") or lang or "en-IN"

        # Update shared state so HybridTTS routes to the correct regional voice
        if detected_lang and detected_lang != "unknown":
            detected_language = detected_lang

        logger.info("Sarvam STT [%s]: %r", detected_lang, transcript[:120])

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(text=transcript, language=detected_lang, confidence=1.0)
            ],
        )


def _empty_event(lang: str) -> stt.SpeechEvent:
    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[stt.SpeechData(text="", language=lang, confidence=0.0)],
    )


def _frames_to_wav(buffer: utils.AudioBuffer) -> bytes:
    """Convert AudioBuffer to WAV bytes (16-bit PCM)."""
    merged = utils.merge_frames(buffer)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(merged.num_channels)
        wf.setsampwidth(2)
        wf.setframerate(merged.sample_rate)
        wf.writeframes(merged.data.tobytes())
    return buf.getvalue()
