"""
Sarvam AI TTS plugin for LiveKit agents (bulbul:v3).

Reads `sarvam_stt.detected_language` to automatically reply in the same
language the caller is speaking. Falls back to `en-IN` if unknown.

Usage in main.py:
    from sarvam_tts import SarvamTTS
    tts = SarvamTTS(api_key=SARVAM_API_KEY)
"""

from __future__ import annotations

import asyncio
import base64
import io
import uuid
import wave
import logging
import os

import httpx
from livekit import rtc
from livekit.agents import tts, utils
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

logger = logging.getLogger(__name__)

_http_client = httpx.AsyncClient(timeout=60.0)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SAMPLE_RATE    = 22050
NUM_CHANNELS   = 1

# bulbul:v3 has 38 speakers — all work across all Indian languages
LANGUAGE_SPEAKERS: dict[str, str] = {
    "hi-IN": "ishita", "te-IN": "ishita", "ta-IN": "ishita",
    "kn-IN": "ishita", "ml-IN": "ishita", "mr-IN": "ishita",
    "bn-IN": "ishita", "gu-IN": "ishita", "od-IN": "ishita",
    "pa-IN": "ishita", "en-IN": "ishita",
}


class SarvamTTS(tts.TTS):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        speaker: str = "ishita",
        model: str = "bulbul:v3",
        pace: float = 1.0,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._api_key = api_key or os.getenv("SARVAM_API_KEY", "")
        self._speaker = speaker
        self._model   = model
        self._pace    = pace

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "sarvam"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "_SarvamChunkedStream":
        return _SarvamChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            api_key=self._api_key,
            speaker=self._speaker,
            model=self._model,
            pace=self._pace,
        )


class _SarvamChunkedStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: SarvamTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        api_key: str,
        speaker: str,
        model: str,
        pace: float,
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._api_key = api_key
        self._speaker = speaker
        self._model   = model
        self._pace    = pace

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        # Detect language from the text script first (reliable for language-switched responses)
        # Fall back to STT detected_language for Latin/English text
        text = self._input_text
        script_lang = _detect_script_language(text)
        if script_lang:
            lang = script_lang
        else:
            try:
                from sarvam_stt import detected_language
                lang = detected_language if detected_language else "en-IN"
            except Exception:
                lang = "en-IN"

        speaker = self._speaker  # user-selected voice takes priority

        # Sarvam TTS has a 500-char limit per request — chunk if needed
        text = self._input_text
        chunks = [text[i:i+500] for i in range(0, len(text), 500)] if text else [""]

        sem = asyncio.Semaphore(3)

        async def _fetch_chunk(chunk: str) -> tuple[bytes, int]:
            async with sem:
                for attempt in range(2):
                    try:
                        resp = await _http_client.post(
                            SARVAM_TTS_URL,
                            headers={
                                "api-subscription-key": self._api_key,
                                "Content-Type": "application/json",
                            },
                            json={
                                "inputs": [chunk],
                                "target_language_code": lang,
                                "speaker": speaker,
                                "model": self._model,
                                "pace": self._pace,
                                "speech_sample_rate": SAMPLE_RATE,
                                "enable_preprocessing": True,
                            },
                            timeout=60.0,
                        )
                        resp.raise_for_status()
                        b64 = (resp.json().get("audios") or [""])[0]
                        if b64:
                            return _wav_to_pcm_with_rate(base64.b64decode(b64))
                        break
                    except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                        if attempt == 0:
                            logger.warning("Sarvam TTS timeout, retrying… (%s)", e)
                            continue
                        logger.error("Sarvam TTS timeout after retry, skipping chunk")
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 503 and attempt == 0:
                            logger.warning("Sarvam TTS 503, retrying…")
                            continue
                        logger.error("Sarvam TTS HTTP %s: %s", e.response.status_code, e.response.text)
                    except Exception as e:
                        logger.error("Sarvam TTS error: %s", e)
                    break
            return b"", SAMPLE_RATE

        active_chunks = [c for c in chunks if c.strip()]
        results = await asyncio.gather(*[_fetch_chunk(c) for c in active_chunks])

        actual_sample_rate = SAMPLE_RATE
        all_pcm: list[bytes] = []
        for pcm_bytes, sr in results:
            if pcm_bytes:
                all_pcm.append(pcm_bytes)
                actual_sample_rate = sr

        if not all_pcm:
            return

        combined_pcm = b"".join(all_pcm)
        request_id = str(uuid.uuid4())

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=actual_sample_rate,
            num_channels=NUM_CHANNELS,
            mime_type=f"audio/pcm;rate={actual_sample_rate}",
        )
        output_emitter.push(combined_pcm)
        output_emitter.end_input()

        logger.info(
            "Sarvam TTS [%s / %s]: %d chars → %d bytes PCM @ %dHz",
            lang, speaker, len(self._input_text), len(combined_pcm), actual_sample_rate,
        )


def _wav_to_pcm_with_rate(wav_bytes: bytes) -> tuple[bytes, int]:
    """Strip WAV header and return (raw 16-bit PCM bytes, actual_sample_rate)."""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        return wf.readframes(wf.getnframes()), wf.getframerate()


def _wav_to_pcm(wav_bytes: bytes) -> bytes:
    """Legacy — strip WAV header and return raw 16-bit PCM bytes."""
    pcm, _ = _wav_to_pcm_with_rate(wav_bytes)
    return pcm


def _detect_script_language(text: str) -> str | None:
    """Detect language from Unicode script ranges in text — more reliable than STT lang for TTS."""
    for char in text:
        cp = ord(char)
        if 0x0B80 <= cp <= 0x0BFF: return "ta-IN"   # Tamil
        if 0x0C00 <= cp <= 0x0C7F: return "te-IN"   # Telugu
        if 0x0C80 <= cp <= 0x0CFF: return "kn-IN"   # Kannada
        if 0x0D00 <= cp <= 0x0D7F: return "ml-IN"   # Malayalam
        if 0x0980 <= cp <= 0x09FF: return "bn-IN"   # Bengali
        if 0x0A80 <= cp <= 0x0AFF: return "gu-IN"   # Gujarati
        if 0x0A00 <= cp <= 0x0A7F: return "pa-IN"   # Punjabi
        if 0x0B00 <= cp <= 0x0B7F: return "od-IN"   # Odia
        if 0x0900 <= cp <= 0x097F: return "hi-IN"   # Devanagari (Hindi/Marathi)
    return None  # Latin/unknown — fall back to STT detected language


