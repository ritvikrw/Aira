"""
HybridTTS — routes all languages through Cartesia Sonic-3 when a Cartesia key is set.
Falls back to Sarvam (Indian scripts) + OpenAI/ElevenLabs (English) when no Cartesia key.

Cartesia language → voice mapping (all tested, all return audio):
  en → Kiara  (Indian-accented English, upbeat)
  hi → Kavita (Customer Care Agent, mature Indian female)
  te → Ramya  (Graceful Host, warm Telugu female)
  ta → Kavitha (Clear Communicator, crisp Tamil female)
  kn → Divya  (Joyful Narrator, lively Kannada female)
  ml → Latha  (Friendly Host, clear Malayalam female)

All audio emitted at 24 000 Hz PCM. Sarvam path resamples from 22 050 Hz.
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

SARVAM_TTS_URL    = "https://api.sarvam.ai/text-to-speech"
OPENAI_TTS_URL    = "https://api.openai.com/v1/audio/speech"
ELEVEN_TTS_URL    = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
CARTESIA_TTS_SSE  = "https://api.cartesia.ai/tts/sse"
CARTESIA_VERSION  = "2024-06-10"
CARTESIA_MODEL    = "sonic-3"   # sonic-3 supports all 5 Indian languages + English

SARVAM_SAMPLE_RATE = 22050
OPENAI_SAMPLE_RATE = 24000
ELEVEN_SAMPLE_RATE = 24000   # ElevenLabs called with pcm_24000 format

# Cartesia: script language code → (voice_id, cartesia_lang_code)
# All voices tested and confirmed working with sonic-3.
CARTESIA_LANG_VOICES: dict[str, tuple[str, str]] = {
    "en":    ("f039066f-cdb7-45ed-b51d-1034ae2f04a0", "en"),  # Cindy — smooth welcoming receptionist
    "hi":    ("56e35e2d-6eb6-4226-ab8b-9776515a7094", "hi"),  # Kavita — Customer Care Agent
    "te":    ("cf061d8b-a752-4865-81a2-57570a6e0565", "te"),  # Ramya — Graceful Host
    "ta":    ("cf061d8b-a752-4865-81a2-57570a6e0565", "te"),  # Ramya (Telugu voice for Tamil)
    "kn":    ("7c6219d2-e8d2-462c-89d8-7ecba7c75d65", "kn"),  # Divya — Joyful Narrator
    "ml":    ("b426013c-002b-4e89-8874-8cd20b68373a", "ml"),  # Latha — Friendly Host
}

# Reverse map: Cartesia voice UUID → language code
# Covers all voices available in the frontend voice picker.
# The selected voice_id determines the TTS language — no text inspection needed.
CARTESIA_VOICE_LANG: dict[str, str] = {
    # English
    "f039066f-cdb7-45ed-b51d-1034ae2f04a0": "en",  # Cindy (default)
    "f8f5f1b2-f02d-4d8e-a40d-fd850a487b3d": "en",  # Kiara
    "a7a59115-2425-4192-844c-1e98ec7d6877": "en",  # Amber
    "d46abd1d-2d02-43e8-819f-51fb652c1c61": "en",  # Grant
    # Hindi
    "56e35e2d-6eb6-4226-ab8b-9776515a7094": "hi",  # Kavita
    "bec003e2-3cb3-429c-8468-206a393c67ad": "hi",  # Parvati
    "47f3bbb1-e98f-4e0c-92c5-5f0325e1e206": "hi",  # Neha
    # Telugu
    "cf061d8b-a752-4865-81a2-57570a6e0565": "te",  # Ramya
    "4418bb06-8329-49a1-bb11-53bb64ca0547": "te",  # Shanti
    # Tamil
    "7f98e662-142d-41ba-89a2-12452640ce6d": "ta",  # Lakshmi — upbeat
    "25d2c432-139c-4035-bfd6-9baaabcdd006": "ta",  # Kavya
    # Kannada
    "7c6219d2-e8d2-462c-89d8-7ecba7c75d65": "kn",  # Divya
    # Malayalam
    "b426013c-002b-4e89-8874-8cd20b68373a": "ml",  # Latha
}

# Sarvam fallback speakers (used when Cartesia key is NOT set)
BEST_SPEAKERS: dict[str, str] = {
    "te-IN": "kavitha", "ta-IN": "anushka", "kn-IN": "roopa",
    "ml-IN": "niharika", "hi-IN": "ishita", "mr-IN": "ishita",
    "bn-IN": "ritu", "gu-IN": "suhani", "pa-IN": "simran",
    "od-IN": "ishita", "en-IN": "ishita",
}


async def synthesize_cartesia(text: str, cartesia_key: str, voice_id: str, lang: str = "en") -> bytes:
    """Synthesize text via Cartesia and return raw PCM bytes at 24000 Hz.
    Returns empty bytes on error. Used for fillers to allow gate-check after synthesis."""
    import json
    total = bytearray()
    try:
        async with _http_client.stream(
            "POST", CARTESIA_TTS_SSE,
            headers={"X-API-Key": cartesia_key, "Cartesia-Version": CARTESIA_VERSION,
                     "Content-Type": "application/json"},
            json={"model_id": CARTESIA_MODEL, "transcript": text,
                  "voice": {"mode": "id", "id": voice_id},
                  "output_format": {"container": "raw", "encoding": "pcm_s16le",
                                    "sample_rate": OPENAI_SAMPLE_RATE},
                  "language": lang},
            timeout=15.0,
        ) as resp:
            if resp.status_code != 200:
                return b""
            sse_buf = ""
            async for raw in resp.aiter_text(chunk_size=4096):
                sse_buf += raw
                while "\n\n" in sse_buf:
                    event, sse_buf = sse_buf.split("\n\n", 1)
                    for line in event.strip().splitlines():
                        if not line.startswith("data: "):
                            continue
                        p = line[6:]
                        if p == "[DONE]":
                            break
                        try:
                            d = json.loads(p).get("data", "")
                            if d:
                                total.extend(base64.b64decode(d))
                        except Exception:
                            pass
    except Exception as e:
        logger.warning("synthesize_cartesia error: %s", e)
    return bytes(total)


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
        cartesia_api_key: str = "",
        cartesia_voice_id: str = "",
        openai_api_key: str = "",
        openai_voice: str = "nova",
        eleven_api_key: str = "",
        eleven_voice_id: str = "",
        eleven_model: str = "eleven_turbo_v2_5",
    ):
        # phrase → pre-synthesized PCM bytes for instant zero-latency playback
        self._phrase_cache: dict[str, bytes] = {}
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=OPENAI_SAMPLE_RATE,   # 24 000 Hz — canonical for all providers
            num_channels=1,
        )
        self._sarvam_key      = sarvam_api_key
        self._sarvam_speaker  = sarvam_speaker
        self._speaker_explicit = sarvam_speaker_explicit
        self._sarvam_model    = sarvam_model
        self._cartesia_key    = cartesia_api_key
        self._cartesia_voice  = cartesia_voice_id
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

    async def cache_phrase(self, text: str, voice_id: str | None = None, lang: str = "en") -> None:
        """Pre-synthesize a short phrase via Cartesia and store PCM for instant zero-latency playback."""
        if not self._cartesia_key or not text.strip():
            return
        v = voice_id or self._cartesia_voice
        try:
            pcm = await synthesize_cartesia(text, self._cartesia_key, v, lang)
            if pcm:
                self._phrase_cache[text] = pcm
                logger.info("Cached phrase [%s] %r: %d bytes", lang, text, len(pcm))
        except Exception as e:
            logger.warning("cache_phrase failed for %r: %s", text, e)

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
            phrase_cache=self._phrase_cache,   # pass directly — no attribute-chain guesswork
            sarvam_key=self._sarvam_key,
            sarvam_speaker=self._sarvam_speaker,
            sarvam_speaker_explicit=self._speaker_explicit,
            sarvam_model=self._sarvam_model,
            cartesia_key=self._cartesia_key,
            cartesia_voice=self._cartesia_voice,
            openai_key=self._openai_key,
            openai_voice=self._openai_voice,
            eleven_key=self._eleven_key,
            eleven_voice=self._eleven_voice,
            eleven_model=self._eleven_model,
        )


class _HybridChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts, input_text, conn_options,
                 phrase_cache,
                 sarvam_key, sarvam_speaker, sarvam_speaker_explicit, sarvam_model,
                 cartesia_key, cartesia_voice,
                 openai_key, openai_voice,
                 eleven_key, eleven_voice, eleven_model):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._phrase_cache    = phrase_cache   # direct ref — no attribute-chain needed
        self._sarvam_key      = sarvam_key
        self._sarvam_speaker  = sarvam_speaker
        self._speaker_explicit = sarvam_speaker_explicit
        self._sarvam_model    = sarvam_model
        self._cartesia_key    = cartesia_key
        self._cartesia_voice  = cartesia_voice
        self._openai_key      = openai_key
        self._openai_voice    = openai_voice
        self._eleven_key      = eleven_key
        self._eleven_voice    = eleven_voice
        self._eleven_model    = eleven_model

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        text = self._input_text
        if not text or not text.strip():
            return

        # Always initialize emitter first — livekit calls end_input() after _run()
        # returns regardless of whether we pushed audio, so initialize must always fire.
        output_emitter.initialize(
            request_id=str(uuid.uuid4()),
            sample_rate=OPENAI_SAMPLE_RATE,
            num_channels=1,
            mime_type=f"audio/pcm;rate={OPENAI_SAMPLE_RATE}",
        )

        try:
            # Cache hit — push pre-synthesized PCM instantly, no network round-trip.
            if text in self._phrase_cache:
                pcm = self._phrase_cache[text]
                output_emitter.push(pcm)
                logger.info("HybridTTS cache hit: %r (%d bytes)", text[:30], len(pcm))
                return

            # Switch filler always uses English voice regardless of locked language.
            _ENGLISH_ONLY_PHRASES = {"Sure, switching now!"}

            # Route: all languages → Cartesia (language-specific voice), fallback OpenAI
            try:
                from sarvam_stt import _locked_language
                locked = _locked_language
            except ImportError:
                locked = None

            if self._cartesia_key:
                if locked and locked != "en-IN" and text not in _ENGLISH_ONLY_PHRASES:
                    lang_code = locked.split("-")[0]  # "te-IN" → "te"
                    voice_id, cartesia_lang = CARTESIA_LANG_VOICES.get(lang_code, CARTESIA_LANG_VOICES["en"])
                    logger.info("HybridTTS → Cartesia [%s] voice=%s", cartesia_lang, voice_id[:8])
                    await self._run_cartesia(output_emitter, text, cartesia_lang, voice_id)
                else:
                    logger.info("HybridTTS → Cartesia [en] voice=%s", self._cartesia_voice[:8])
                    await self._run_cartesia(output_emitter, text, "en", self._cartesia_voice)
            elif self._openai_key:
                logger.info("HybridTTS → OpenAI [%s]", self._openai_voice)
                await self._run_openai(output_emitter, text)
            elif self._eleven_key and self._eleven_voice:
                logger.info("HybridTTS → ElevenLabs")
                await self._run_elevenlabs(output_emitter, text)
            else:
                logger.warning("HybridTTS: no TTS provider configured")
        finally:
            output_emitter.end_input()

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
        if pcm:
            output_emitter.push(pcm)
        else:
            logger.warning("Sarvam TTS returned empty audio for [%s] — no audio played", lang)

    async def _run_cartesia(
        self,
        output_emitter: tts.AudioEmitter,
        text: str,
        language: str = "en",
        voice_id: str | None = None,
    ) -> None:
        """Streaming Cartesia Sonic-3 TTS — all 6 languages, first audio ~90ms via SSE."""
        import json
        if not voice_id:
            voice_id, language = CARTESIA_LANG_VOICES.get(language, CARTESIA_LANG_VOICES["en"])
        try:
            total_bytes = 0
            async with _http_client.stream(
                "POST", CARTESIA_TTS_SSE,
                headers={
                    "X-API-Key": self._cartesia_key,
                    "Cartesia-Version": CARTESIA_VERSION,
                    "Content-Type": "application/json",
                },
                json={
                    "model_id": CARTESIA_MODEL,
                    "transcript": text,
                    "voice": {"mode": "id", "id": voice_id},
                    "output_format": {
                        "container": "raw",
                        "encoding": "pcm_s16le",
                        "sample_rate": OPENAI_SAMPLE_RATE,
                    },
                    "language": language,
                },
                timeout=30.0,
            ) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    logger.error("Cartesia TTS HTTP %s: %s", resp.status_code, body[:200])
                    # For non-English, fall back to Sarvam to preserve regional voice
                    # For English, fall back to OpenAI
                    try:
                        from sarvam_stt import _locked_language
                        locked = _locked_language
                    except ImportError:
                        locked = ""
                    if locked and locked != "en-IN" and self._sarvam_key:
                        await self._run_sarvam(output_emitter, text, locked)
                    elif self._openai_key:
                        await self._run_openai(output_emitter, text)
                    return

                # Parse SSE stream — each event is "data: <json>\n\n"
                sse_buf = ""
                async for raw in resp.aiter_text(chunk_size=4096):
                    sse_buf += raw
                    while "\n\n" in sse_buf:
                        event, sse_buf = sse_buf.split("\n\n", 1)
                        for line in event.strip().splitlines():
                            if not line.startswith("data: "):
                                continue
                            payload_str = line[6:]
                            if payload_str == "[DONE]":
                                break
                            try:
                                payload = json.loads(payload_str)
                                audio_b64 = payload.get("data", "")
                                if audio_b64:
                                    pcm = base64.b64decode(audio_b64)
                                    output_emitter.push(pcm)
                                    total_bytes += len(pcm)
                            except Exception:
                                pass

            logger.info("Cartesia TTS [%s]: %d chars → %d bytes@24000Hz",
                        self._cartesia_voice[:8], len(text), total_bytes)
        except Exception as e:
            logger.error("Cartesia TTS error: %s", e)
            try:
                from sarvam_stt import _locked_language
                locked = _locked_language
            except ImportError:
                locked = ""
            if locked and locked != "en-IN" and self._sarvam_key:
                logger.info("Cartesia failed — falling back to Sarvam for %s", locked)
                await self._run_sarvam(output_emitter, text, locked)
            elif self._openai_key:
                logger.info("Cartesia failed — falling back to OpenAI")
                await self._run_openai(output_emitter, text)

    async def _run_openai(self, output_emitter: tts.AudioEmitter, text: str) -> None:
        """Streaming OpenAI TTS — first audio chunk plays in ~200 ms."""
        try:
            total_bytes = 0
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
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if chunk:
                        output_emitter.push(chunk)
                        total_bytes += len(chunk)
            logger.info("OpenAI TTS [%s]: %d chars → %d bytes@24000Hz",
                        self._openai_voice, len(text), total_bytes)
        except Exception as e:
            logger.error("OpenAI TTS streaming error: %s", e)

    async def _run_elevenlabs(self, output_emitter: tts.AudioEmitter, text: str) -> None:
        """Streaming ElevenLabs TTS — first audio chunk plays in ~200 ms, same as OpenAI."""
        url = ELEVEN_TTS_URL.format(voice_id=self._eleven_voice)
        try:
            total_bytes = 0
            async with _http_client.stream(
                "POST", url,
                headers={"xi-api-key": self._eleven_key,
                         "Content-Type": "application/json"},
                json={"text": text, "model_id": self._eleven_model,
                      "output_format": "pcm_24000"},
                timeout=30.0,
            ) as resp:
                if resp.status_code != 200:
                    logger.error("ElevenLabs TTS HTTP %s", resp.status_code)
                    return
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if chunk:
                        output_emitter.push(chunk)
                        total_bytes += len(chunk)
            logger.info("ElevenLabs TTS [%s]: %d chars → %d bytes@24000Hz",
                        self._eleven_voice, len(text), total_bytes)
        except Exception as e:
            logger.error("ElevenLabs TTS streaming error: %s", e)
