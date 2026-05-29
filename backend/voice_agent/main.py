import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime

# Fix Windows terminal encoding so livekit-agents rich output doesn't crash
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv()

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents import AgentSession
from livekit.agents.tts import StreamAdapter as TtsStreamAdapter
from livekit.agents.stt import StreamAdapter as SttStreamAdapter
from livekit.plugins import deepgram, elevenlabs, openai as lk_openai, silero
from hybrid_tts import HybridTTS
from sarvam_stt import SarvamSTT

import httpx
from agent import ReceptionistAgent, end_call

_api_client = httpx.AsyncClient(timeout=5.0)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

OPENAI_VOICES = {"alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"}


async def fetch_settings() -> dict:
    try:
        res = await _api_client.get(f"{API_BASE_URL}/settings")
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        logger.warning("Could not fetch settings: %s", e)
    return {}


async def _save_transcript(session_id: str, speaker: str, message: str) -> None:
    try:
        await _api_client.post(
            f"{API_BASE_URL}/transcripts/",
            json={"session_id": session_id, "speaker": speaker, "message": message},
        )
    except Exception as e:
        logger.warning("Failed to save transcript: %s", e)


async def _save_metrics(session_id: str, metrics, tts_provider: str | None = None) -> None:
    try:
        from livekit.agents.metrics import LLMMetrics, TTSMetrics, STTMetrics
        payload: dict = {}
        if tts_provider is not None:
            # Initial call just to record the provider name
            payload = {"tts_provider": tts_provider}
        elif isinstance(metrics, LLMMetrics):
            payload = {
                "llm_prompt_tokens": getattr(metrics, "prompt_tokens", 0) or 0,
                "llm_completion_tokens": getattr(metrics, "completion_tokens", 0) or 0,
                "llm_ttft_ms": round(getattr(metrics, "ttft", 0) * 1000, 1) if getattr(metrics, "ttft", None) else None,
                "llm_requests": 1,
            }
        elif isinstance(metrics, TTSMetrics):
            payload = {
                "tts_characters": getattr(metrics, "characters_count", 0) or 0,
                "tts_ttfb_ms": round(getattr(metrics, "ttfb", 0) * 1000, 1) if getattr(metrics, "ttfb", None) else None,
                "tts_requests": 1,
            }
        elif isinstance(metrics, STTMetrics):
            # duration = total request time (0.0 for streaming STT, actual ms for batch Sarvam)
            stt_duration = getattr(metrics, "duration", None)
            payload = {
                "stt_audio_duration_ms": round((getattr(metrics, "audio_duration", 0) or 0) * 1000, 1),
                "stt_ttft_ms": round(stt_duration * 1000, 1) if stt_duration else None,
                "stt_requests": 1,
            }
        if payload:
            await _api_client.post(f"{API_BASE_URL}/internal/metrics/{session_id}", json=payload)
            logger.debug("Saved metrics for %s: %s", session_id, type(metrics).__name__ if metrics else "provider")
    except Exception as e:
        logger.warning("Failed to save metrics: %s", e)


def _resolve_caller_phone(caller_id: str | None) -> str:
    """Return E.164 phone for Twilio calls, dummy number for web/test calls."""
    if not caller_id:
        return "+00 00000 00000"
    # Twilio caller IDs look like +919876543210 or sip:+919876543210@...
    if caller_id.startswith("sip:"):
        # extract number from sip:+number@host
        part = caller_id.split("sip:")[1].split("@")[0]
        return part if part.startswith("+") else f"+{part}"
    if caller_id.startswith("+") or caller_id.lstrip("-").isdigit():
        return caller_id
    # Web / test call
    return "+00 00000 00000"


async def register_call(session_id: str, room_name: str, caller_id: str | None, start_time: str) -> None:
    """Create the call_log row immediately so transcript FK inserts succeed during the call."""
    caller_phone = _resolve_caller_phone(caller_id)
    try:
        await _api_client.post(
            f"{API_BASE_URL}/calls/",
            json={"session_id": session_id, "room_name": room_name, "caller_id": caller_id,
                  "caller_phone": caller_phone, "start_time": start_time},
            timeout=5.0,
        )
        logger.info("Call registered: %s (phone=%s)", session_id, caller_phone)
    except Exception as e:
        logger.error("Failed to register call %s: %s", session_id, e)


async def _prewarm_tts(tts) -> None:
    """Synthesize a silent short string to establish the TTS connection before the call starts."""
    try:
        async for _ in tts.synthesize(" "):
            break
    except Exception:
        pass  # prewarm is best-effort


async def _prewarm_sarvam(sarvam_key: str) -> None:
    """Pre-warm Sarvam TTS for the 3 most common Indian languages so the first
    non-English response has no cold-start delay (~1.5 s saved on first Indian reply)."""
    from hybrid_tts import SARVAM_TTS_URL
    prewarms = [
        ("te-IN", "kavitha", "నమస్కారం"),
        ("hi-IN", "ishita",  "नमस्ते"),
        ("ta-IN", "kavitha", "வணக்கம்"),
    ]

    async def _warm_one(lang: str, speaker: str, text: str) -> None:
        try:
            from sarvam_tts import _http_client as _sarvam_http
            await _sarvam_http.post(
                SARVAM_TTS_URL,
                headers={"api-subscription-key": sarvam_key},
                json={
                    "inputs": [text],
                    "target_language_code": lang,
                    "speaker": speaker,
                    "model": "bulbul:v3",
                    "pace": 1.35,
                    "enable_preprocessing": True,
                },
                timeout=10.0,
            )
            logger.debug("Sarvam TTS prewarm done: %s/%s", lang, speaker)
        except Exception as e:
            logger.debug("Sarvam TTS prewarm failed (%s): %s", lang, e)

    await asyncio.gather(*[_warm_one(*p) for p in prewarms])


async def entrypoint(ctx: JobContext) -> None:
    session_id = str(uuid.uuid4())
    room_name = ctx.room.name if ctx.room else "unknown"

    caller_id = None
    if ctx.room:
        for p in ctx.room.remote_participants.values():
            if p.identity:
                caller_id = p.identity
                break

    await ctx.connect()

    call_start_time = datetime.utcnow().isoformat()

    # Fetch settings and register call in parallel
    settings, _ = await asyncio.gather(
        fetch_settings(),
        register_call(session_id, room_name, caller_id, call_start_time),
    )

    agent_name = settings.get("agent_name", "aira")
    org_name = settings.get("org_name", "")
    org_description = settings.get("org_description", "")
    default_language = settings.get("default_language", "en-IN")

    # Pre-set detected_language so TTS uses the right language from the very first word
    if default_language and default_language != "en-IN":
        try:
            import sarvam_stt
            sarvam_stt.detected_language = default_language
            logger.info("Pre-set TTS language to %s", default_language)
        except ImportError:
            pass

    # Build structured instructions block from config fields
    instruction_parts = []
    if settings.get("business_hours"):
        instruction_parts.append(f"Business hours: {settings['business_hours']}")
    if settings.get("human_escalation"):
        instruction_parts.append(f"When caller asks for a human: {settings['human_escalation']}")
    if settings.get("topics_to_avoid"):
        instruction_parts.append(f"Do not discuss: {settings['topics_to_avoid']}")
    if settings.get("custom_instructions"):
        instruction_parts.append(settings["custom_instructions"])
    instructions = "\n".join(instruction_parts)

    sarvam_key  = os.getenv("SARVAM_API_KEY", "")
    openai_key  = os.getenv("OPENAI_API_KEY", "")
    voice_id    = settings.get("selected_voice_id") or os.getenv("ELEVENLABS_VOICE_ID", "nova")
    eleven_key  = os.getenv("ELEVEN_API_KEY", "")
    eleven_model = os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5")

    # --- STT ---
    # Tighter VAD: faster end-of-speech detection, less waiting for silence
    vad = silero.VAD.load(
        min_silence_duration=0.2,       # default ~0.55s — fire sooner after user stops
        prefix_padding_duration=0.3,    # default ~0.5s  — less leading buffer
        activation_threshold=0.5,       # default — keep same
    )
    # Use Sarvam STT when a Sarvam key is present — it handles all Indian languages
    # (Telugu, Tamil, Hindi, Kannada, etc.) and auto-detects which language is spoken.
    # The translate=True mode outputs English text so the LLM always gets clean input,
    # while detected_language is set so TTS replies in the correct language.
    # Fall back to Deepgram for English-only deployments.
    if sarvam_key:
        stt_instance = SttStreamAdapter(
            stt=SarvamSTT(api_key=sarvam_key),   # language="unknown" → auto-detect, native transcript
            vad=vad,
        )
        logger.info("STT provider: Sarvam (saarika:v2.5, native language)")
    else:
        stt_instance = deepgram.STT()
        logger.info("STT provider: Deepgram")

    # --- TTS ---
    # If SARVAM_API_KEY is set, ALWAYS use HybridTTS so Indian-language responses
    # are routed to Sarvam (bulbul:v3) regardless of which English voice is selected.
    # The selected voice only determines the English fallback provider.
    if sarvam_key:
        # Determine Sarvam speaker
        sarvam_speaker_explicit = voice_id.startswith("sarvam:")
        if sarvam_speaker_explicit:
            sarvam_speaker = voice_id.split("sarvam:")[1]
        else:
            sarvam_speaker = "ishita"  # default speaker for non-Sarvam selections

        # Determine English fallback provider
        if voice_id in OPENAI_VOICES:
            # User picked an OpenAI voice → use it for English
            tts = HybridTTS(
                sarvam_api_key=sarvam_key,
                sarvam_speaker=sarvam_speaker,
                sarvam_speaker_explicit=sarvam_speaker_explicit,
                openai_api_key=openai_key,
                openai_voice=voice_id,
            )
            tts_provider = f"Hybrid / Sarvam:{sarvam_speaker} + OpenAI:{voice_id}"
            logger.info("TTS provider: HybridTTS (Sarvam:%s + OpenAI:%s)", sarvam_speaker, voice_id)
        elif eleven_key and not voice_id.startswith("sarvam:") and voice_id not in OPENAI_VOICES:
            # User picked an ElevenLabs voice → use it for English
            tts = HybridTTS(
                sarvam_api_key=sarvam_key,
                sarvam_speaker=sarvam_speaker,
                sarvam_speaker_explicit=sarvam_speaker_explicit,
                eleven_api_key=eleven_key,
                eleven_voice_id=voice_id,
                eleven_model=eleven_model,
            )
            tts_provider = f"Hybrid / Sarvam:{sarvam_speaker} + ElevenLabs:{voice_id}"
            logger.info("TTS provider: HybridTTS (Sarvam:%s + ElevenLabs:%s)", sarvam_speaker, voice_id)
        else:
            # Sarvam voice selected or no other provider — fall back to OpenAI nova for English
            openai_voice = os.getenv("OPENAI_TTS_VOICE", "nova")
            tts = HybridTTS(
                sarvam_api_key=sarvam_key,
                sarvam_speaker=sarvam_speaker,
                sarvam_speaker_explicit=sarvam_speaker_explicit,
                openai_api_key=openai_key,
                openai_voice=openai_voice,
            )
            tts_provider = f"Hybrid / Sarvam:{sarvam_speaker} + OpenAI:{openai_voice}"
            logger.info("TTS provider: HybridTTS (Sarvam:%s + OpenAI:%s)", sarvam_speaker, openai_voice)
    elif voice_id in OPENAI_VOICES:
        # No Sarvam key — use selected provider directly
        tts = lk_openai.TTS(model="tts-1", voice=voice_id)
        tts_provider = f"OpenAI / tts-1 ({voice_id})"
        logger.info("TTS provider: OpenAI (voice=%s)", voice_id)
    elif eleven_key:
        tts = elevenlabs.TTS(voice_id=voice_id, model=eleven_model, api_key=eleven_key)
        tts_provider = f"ElevenLabs / {eleven_model}"
        logger.info("TTS provider: ElevenLabs (voice=%s)", voice_id)
    else:
        # Final fallback — OpenAI nova
        tts = lk_openai.TTS(model="tts-1", voice="nova")
        tts_provider = "OpenAI / tts-1 (nova)"
        logger.info("TTS provider: OpenAI fallback (nova)")

    # Record TTS provider for this session immediately
    asyncio.create_task(_save_metrics(session_id, None, tts_provider=tts_provider))

    # Start Sarvam prewarm in background first so it runs concurrently with TTS prewarm.
    if sarvam_key:
        asyncio.create_task(_prewarm_sarvam(sarvam_key))

    # Pre-warm TTS connection so the greeting has no cold-start delay.
    await _prewarm_tts(tts)

    # Wrap with StreamAdapter so LiveKit feeds text sentence-by-sentence.
    # Each sentence is synthesized and played immediately — audio starts in ~300ms
    # instead of waiting for the full LLM response to finish.
    tts_final = TtsStreamAdapter(tts=tts)

    llm_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    llm = lk_openai.LLM(model=llm_model, temperature=temperature)
    logger.info("LLM provider: OpenAI (%s, temp=%.1f)", llm_model, temperature)

    session = AgentSession(
        vad=vad,
        stt=stt_instance,
        llm=llm,
        tts=tts_final,
        min_endpointing_delay=0.2,   # default 0.5s — start processing sooner after silence
    )

    agent = ReceptionistAgent(session_id=session_id, agent_name=agent_name, org_name=org_name, org_description=org_description, instructions=instructions, default_language=default_language)

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        if participant.identity != ctx.room.local_participant.identity:
            logger.info("Caller disconnected - ending session %s", session_id)
            asyncio.create_task(end_call(session_id, room_name=room_name, caller_id=caller_id, start_time=call_start_time))

    @session.on("conversation_item_added")
    def on_conversation_item_added(ev):
        from livekit.agents.llm.chat_context import ChatMessage as LKChatMessage
        item = ev.item
        if not isinstance(item, LKChatMessage):
            return
        logger.info("conversation_item_added: role=%s text=%r", item.role, item.text_content)
        if item.role == "assistant":
            text = item.text_content
            if text and text.strip():
                asyncio.create_task(_save_transcript(session_id, "agent", text.strip()))
                # Fallback: detect name from agent's acknowledgement (e.g. "Thank you, Somalingam!")
                agent.on_agent_reply(text.strip())

    @session.on("metrics_collected")
    def on_metrics_collected(ev):
        asyncio.create_task(_save_metrics(session_id, ev.metrics))

    await session.start(agent, room=ctx.room)

    await asyncio.sleep(float("inf"))


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, num_idle_processes=0))
