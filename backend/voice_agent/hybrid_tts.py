"""
HybridTTS — routes to Sarvam for Indian language text, OpenAI/ElevenLabs for English.
Detection is script-based (Unicode ranges), so it works automatically mid-conversation.

All audio is normalised to 24 000 Hz (OpenAI's native rate) so LiveKit's pipeline
never sees a sample-rate mismatch between providers.  Sarvam's 22 050 Hz output is
upsampled with a simple linear interpolator before being emitted.
"""

from __future__ import annotations

import asyncio
import struct
import base64
import logging
import uuid

import httpx
from livekit.agents import tts
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions

from sarvam_tts import _detect_script_language, _wav_to_pcm_with_rate

logger = logging.getLogger(__name__)

_http_client = httpx.AsyncClient(timeout=60.0)

SARVAM_TTS_URL  = "https://api.sarvam.ai/text-to-speech"
OPENAI_TTS_URL  = "https://api.openai.com/v1/audio/speech"
ELEVEN_TTS_URL  = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

SARVAM_SAMPLE_RATE = 22050
OPENAI_SAMPLE_RATE = 24000   # canonical output rate for all providers
ELEVEN_SAMPLE_RATE = 22050

# Best Sarvam bulbul:v3 speaker per language — matched to regional naming/phonetics.
BEST_SPEAKERS: dict[str, str] = {
    "te-IN": "kavitha",   # South Indian female, natural Telugu phonetics
    "ta-IN": "kavitha",   # Tamil
    "kn-IN": "roopa",     # Kannada
    "ml-IN": "niharika",  # Malayalam
    "hi-IN": "ishita",    # Hindi — ishita is best for Devanagari
    "mr-IN": "ishita",    # Marathi (Devanagari)
    "bn-IN": "ritu",      # Bengali
    "gu-IN": "suhani",    # Gujarati
    "pa-IN": "simran",    # Punjabi
    "od-IN": "ishita",    # Odia — fallback
    "en-IN": "ishita",    # English fallback
}


def _resample_to_24k(pcm_bytes: bytes, src_rate: int) -> bytes:
    """Upsample/downsample 16-bit signed mono PCM to 24 000 Hz via linear interpolation."""
    if src_rate == OPENAI_SAMPLE_RATE or not pcm_bytes:
        return pcm_bytes
    n = len(pcm_bytes) // 2
    if n == 0:
        return b""
    src = struct.unpack(f"<{n}h", pcm_bytes)
    ratio = src_rate / OPENAI_SAMPLE_RATE
    out_n = max(1, int(n / ratio))
    out: list[int] = []
    for i in range(out_n):
        pos = i * ratio
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        frac = pos - lo
        s = int(src[lo] * (1.0 - frac) + src[hi] * frac)
        out.append(max(-32768, min(32767, s)))
    return struct.pack(f"<{out_n}h", *out)


class HybridTTS(tts.TTS):
    """Routes synthesis to Sarvam (Indian scripts) or OpenAI/ElevenLabs (English).
    All audio is emitted at 24 000 Hz regardless of provider."""

    def __init__(
        self,
        *,
        sarvam_api_key: str,
        sarvam_speaker: str = "ishita",
        sarvam_speaker_explicit: bool = False,
        sarvam_model: str = "bulbul:v3",
        openai_api_key: str = "",
        openai_voice: str = "nova",
        eleven_api_key: str = "",
        eleven_voice_id: str = "",
        eleven_model: str = "eleven_turbo_v2_5",
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=OPENAI_SAMPLE_RATE,   # 24 000 Hz — canonical for all providers
            num_channels=1,
        )
        self._sarvam_key      = sarvam_api_key
        self._sarvam_speaker  = sarvam_speaker
        self._speaker_explicit = sarvam_speaker_explicit
        self._sarvam_model    = sarvam_model
        self._openai_key      = openai_api_key
        self._openai_voice    = openai_voice
        self._eleven_key      = eleven_api_key
        self._eleven_voice    = eleven_voice_id
        self._eleven_model    = eleven_model

    @property
    def model(self) -> str:
        return "hybrid"

    @property
    def provider(self) -> str:
        return "hybrid"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "_HybridChunkedStream":
        return _HybridChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            sarvam_key=self._sarvam_key,
            sarvam_speaker=self._sarvam_speaker,
            sarvam_speaker_explicit=self._speaker_explicit,
            sarvam_model=self._sarvam_model,
            openai_key=self._openai_key,
            openai_voice=self._openai_voice,
            eleven_key=self._eleven_key,
            eleven_voice=self._eleven_voice,
            eleven_model=self._eleven_model,
        )


class _HybridChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts, input_text, conn_options,
                 sarvam_key, sarvam_speaker, sarvam_speaker_explicit, sarvam_model,
                 openai_key, openai_voice,
                 eleven_key, eleven_voice, eleven_model):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._sarvam_key      = sarvam_key
        self._sarvam_speaker  = sarvam_speaker
        self._speaker_explicit = sarvam_speaker_explicit
        self._sarvam_model    = sarvam_model
        self._openai_key      = openai_key
        self._openai_voice    = openai_voice
        self._eleven_key      = eleven_key
        self._eleven_voice    = eleven_voice
        self._eleven_model    = eleven_model

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        text = self._input_text
        if not text or not text.strip():
            return

        script_lang = _detect_script_language(text)

        if script_lang and self._sarvam_key:
            logger.info("HybridTTS → Sarvam [%s]", script_lang)
            await self._run_sarvam(output_emitter, text, script_lang)
        elif self._eleven_key and self._eleven_voice:
            logger.info("HybridTTS → ElevenLabs [en]")
            await self._run_elevenlabs(output_emitter, text)
        elif self._openai_key:
            logger.info("HybridTTS → OpenAI [en]")
            await self._run_openai(output_emitter, text)
        else:
            logger.warning("HybridTTS: no English TTS provider configured")

    # ── helpers ─────────────────────────────────────────────────────────────

    async def _fetch_sarvam_pcm_24k(self, text: str, lang: str, speaker: str) -> bytes:
        """Fetch full Sarvam audio for `text`, return as 24 000 Hz mono PCM.

        Sarvam has a 500-char limit per request — split into chunks, synthesise
        each, concatenate, then resample the combined result to 24 000 Hz once
        (avoids resampling boundary artefacts between chunks).
        """
        parts = [c for c in (text[i:i + 500] for i in range(0, len(text), 500)) if c.strip()]

        sem = asyncio.Semaphore(3)

        async def _fetch_chunk(chunk: str) -> tuple[bytes, int]:
            async with sem:
                for attempt in range(2):
                    try:
                        resp = await _http_client.post(
                            SARVAM_TTS_URL,
                            headers={"api-subscription-key": self._sarvam_key,
                                     "Content-Type": "application/json"},
                            json={"inputs": [chunk], "target_language_code": lang,
                                  "speaker": speaker,
                                  "model": self._sarvam_model, "pace": 1.35,
                                  "enable_preprocessing": True},
                            timeout=60.0,
                        )
                        resp.raise_for_status()
                        b64 = (resp.json().get("audios") or [""])[0]
                        if b64:
                            return _wav_to_pcm_with_rate(base64.b64decode(b64))
                        break
                    except (httpx.ReadTimeout, httpx.ConnectTimeout):
                        if attempt == 0:
                            logger.warning("Sarvam TTS timeout, retrying…")
                            continue
                        logger.error("Sarvam TTS timeout after retry — skipping chunk")
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 503 and attempt == 0:
                            logger.warning("Sarvam TTS 503, retrying…")
                            continue
                        logger.error("Sarvam TTS HTTP %s: %s", e.response.status_code, e.response.text)
                    except Exception as e:
                        logger.error("Sarvam TTS error: %s", e)
                    break
            return b"", SARVAM_SAMPLE_RATE

        results = await asyncio.gather(*[_fetch_chunk(p) for p in parts])
        actual_rate = SARVAM_SAMPLE_RATE
        raw_pcm_parts: list[bytes] = []
        for pcm, rate in results:
            if pcm:
                raw_pcm_parts.append(pcm)
                actual_rate = rate

        if not raw_pcm_parts:
            return b""

        combined_native = b"".join(raw_pcm_parts)
        pcm_24k = _resample_to_24k(combined_native, actual_rate)
        logger.info("Sarvam TTS [%s]: %d chars → %d bytes native@%dHz → %d bytes@24000Hz",
                    lang, len(text), len(combined_native), actual_rate, len(pcm_24k))
        return pcm_24k

    # ── providers ────────────────────────────────────────────────────────────

    async def _run_sarvam(self, output_emitter: tts.AudioEmitter,
                          text: str, lang: str) -> None:
        # Use explicit user-selected speaker; otherwise pick best per-language default.
        speaker = self._sarvam_speaker if self._speaker_explicit else BEST_SPEAKERS.get(lang, self._sarvam_speaker)

        pcm = await self._fetch_sarvam_pcm_24k(text, lang, speaker)
        if not pcm:
            return

        output_emitter.initialize(
            request_id=str(uuid.uuid4()),
            sample_rate=OPENAI_SAMPLE_RATE,   # always 24 000 Hz
            num_channels=1,
            mime_type=f"audio/pcm;rate={OPENAI_SAMPLE_RATE}",
        )
        output_emitter.push(pcm)
        output_emitter.end_input()

    async def _run_openai(self, output_emitter: tts.AudioEmitter, text: str) -> None:
        """Streaming OpenAI TTS — first audio chunk plays in ~200 ms."""
        try:
            total_bytes = 0
            initialized = False
            async with _http_client.stream(
                "POST", OPENAI_TTS_URL,
                headers={"Authorization": f"Bearer {self._openai_key}",
                         "Content-Type": "application/json"},
                json={"model": "tts-1", "voice": self._openai_voice,
                      "input": text, "response_format": "pcm"},
                timeout=30.0,
            ) as resp:
                if resp.status_code != 200:
                    logger.error("OpenAI TTS HTTP %s", resp.status_code)
                    return
                output_emitter.initialize(
                    request_id=str(uuid.uuid4()),
                    sample_rate=OPENAI_SAMPLE_RATE,
                    num_channels=1,
                    mime_type=f"audio/pcm;rate={OPENAI_SAMPLE_RATE}",
                )
                initialized = True
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if chunk:
                        output_emitter.push(chunk)
                        total_bytes += len(chunk)
            if initialized:
                output_emitter.end_input()
                logger.info("OpenAI TTS [%s] streaming: %d chars → %d bytes@24000Hz",
                            self._openai_voice, len(text), total_bytes)
        except Exception as e:
            logger.error("OpenAI TTS streaming error: %s", e)

    async def _run_elevenlabs(self, output_emitter: tts.AudioEmitter, text: str) -> None:
        url = ELEVEN_TTS_URL.format(voice_id=self._eleven_voice)
        try:
            resp = await _http_client.post(
                url,
                headers={"xi-api-key": self._eleven_key,
                         "Content-Type": "application/json"},
                json={"text": text, "model_id": self._eleven_model,
                      "output_format": "pcm_24000"},   # request 24 000 Hz directly
                timeout=30.0,
            )
            resp.raise_for_status()
            pcm = resp.content
        except Exception as e:
            logger.error("ElevenLabs TTS error: %s", e)
            return

        if not pcm:
            return

        output_emitter.initialize(request_id=str(uuid.uuid4()),
                                  sample_rate=OPENAI_SAMPLE_RATE,
                                  num_channels=1,
                                  mime_type=f"audio/pcm;rate={OPENAI_SAMPLE_RATE}")
        output_emitter.push(pcm)
        output_emitter.end_input()
        logger.info("ElevenLabs TTS [%s]: %d chars → %d bytes@24000Hz",
                    self._eleven_voice, len(text), len(pcm))
