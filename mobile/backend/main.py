import asyncio
import os
import sys
import logging
import re
import uuid
import json
import random
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import httpx
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Reconfigure stdout/stderr for Unicode compatibility
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure prompts package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("PipecatWSBackend")

load_dotenv()

# Import Pipecat core
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.frames.frames import (
    Frame,
    EndFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    StartFrame,
    LLMRunFrame,
    TranscriptionFrame,
    TextFrame,
    LLMFullResponseEndFrame,
    TTSSpeakFrame,
    InterruptionFrame,
    ErrorFrame
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection

# Import VAD with dynamic import protection for onnxruntime DLL issue on Windows
try:
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams
    from pipecat.processors.audio.vad_processor import VADProcessor
    _VAD_AVAILABLE = True
except Exception as e:
    logger = logging.getLogger("PipecatWSBackend")
    logger.warning(f"Failed to load Silero VAD (e.g. due to onnxruntime DLL issue on Windows): {e}")
    _VAD_AVAILABLE = False

# Import Pipecat services
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.sarvam.stt import SarvamSTTService
from pipecat.services.sarvam.tts import SarvamTTSService
from pipecat.services.llm_service import FunctionCallParams

# Import custom WebSocket Transport from server
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.serializers.base_serializer import FrameSerializer

# Import context/aggregators
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair, LLMUserAggregatorParams
from pipecat.turns.user_turn_strategies import UserTurnStrategies, TranscriptionUserTurnStartStrategy, ExternalUserTurnStopStrategy
try:
    from pipecat.turns.user_turn_strategies import VADUserTurnStartStrategy
    _VAD_TURN_STRAT_AVAILABLE = True
except Exception:
    _VAD_TURN_STRAT_AVAILABLE = False

# Import prompt builder
from prompts import build_prompt

# Database and API configurations
DATABASE_URL = os.getenv("DATABASE_URL_AIRA", os.getenv("DATABASE_URL", "postgresql://recep:recep@localhost:5432/recep"))
if "postgresql+asyncpg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

API_BASE_URL = os.getenv("API_BASE_URL_AIRA", "http://localhost:8000")
db_pool = None
# Registry of active session prompt-refresh callbacks: session_id → async callable
_session_prompt_updaters: dict = {}

# Initialize FastAPI app for HTTP endpoints
api_app = FastAPI(title="AIRA Mobile API")
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API Endpoints for Android Client
@api_app.get("/settings")
async def get_settings():
    if not db_pool:
        logger.warning("DB offline - returning default settings")
        return {
            "selected_voice_id": "cartesia:f039066f-cdb7-45ed-b51d-1034ae2f04a0",
            "default_language": "en-IN",
            "agent_name": "AIRA",
            "org_name": "AIRA Solutions",
            "org_description": "We provide premium AI voice receptionist systems.",
            "custom_instructions": "Be polite, helpful, and professional.",
            "business_hours": "9 AM to 5 PM, Monday to Friday",
            "human_escalation": "Transfer to our support line at +1-800-555-0199",
            "topics_to_avoid": "Do not discuss legal advice or product pricing guarantees."
        }
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM agent_settings")
            return {row['key']: row['value'] for row in rows}
    except Exception as e:
        logger.error("API failed to get settings: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_app.post("/settings")
async def update_settings(settings: dict):
    if not db_pool:
        logger.warning("DB offline - cannot save settings")
        return {"status": "success", "warning": "database offline"}
    try:
        async with db_pool.acquire() as conn:
            for k, v in settings.items():
                await conn.execute("""
                    INSERT INTO agent_settings (key, value) VALUES ($1, $2)
                    ON CONFLICT (key) DO UPDATE SET value = $2
                """, k, str(v))
            # Fetch complete merged settings to push to active sessions
            rows = await conn.fetch("SELECT key, value FROM agent_settings")
            all_settings = {row['key']: row['value'] for row in rows}
        # Refresh prompts in all active calls
        for cb in list(_session_prompt_updaters.values()):
            asyncio.create_task(cb(all_settings))
        return {"status": "success"}
    except Exception as e:
        logger.error("API failed to update settings: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/calls")
async def get_calls():
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT session_id, caller_id, caller_name, status, call_start_time, call_end_time, call_duration_seconds, is_simulation, llm_ttft_ms, total_latency_ms 
                FROM call_logs 
                ORDER BY call_start_time DESC
            """)
            calls = []
            for r in rows:
                calls.append({
                    "session_id": r['session_id'],
                    "caller_phone": r['caller_id'] or "Unknown",
                    "caller_name": r['caller_name'] or "Incoming Call",
                    "status": r['status'],
                    "call_start_time": r['call_start_time'].isoformat() if r['call_start_time'] else None,
                    "call_end_time": r['call_end_time'].isoformat() if r['call_end_time'] else None,
                    "call_duration_seconds": r['call_duration_seconds'],
                    "is_simulation": r.get('is_simulation', False) if hasattr(r, 'get') else r['is_simulation'],
                    "llm_ttft_ms": r.get('llm_ttft_ms', 0) if hasattr(r, 'get') else r['llm_ttft_ms'],
                    "total_latency_ms": r.get('total_latency_ms', 0) if hasattr(r, 'get') else r['total_latency_ms']
                })
            return calls
    except Exception as e:
        logger.error("API failed to get calls: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/transcripts/{session_id}")
async def get_transcripts(session_id: str):
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT speaker, message, created_at 
                FROM transcripts 
                WHERE session_id = $1 
                ORDER BY id
            """, session_id)
            return [{
                "speaker": r['speaker'],
                "message": r['message'],
                "created_at": r['created_at'].isoformat() if r['created_at'] else None
            } for r in rows]
    except Exception as e:
        logger.error("API failed to get transcripts: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# Database Initialization
async def init_db():
    conn = None
    try:
        conn = await asyncpg.connect(DATABASE_URL, statement_cache_size=0)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                session_id      VARCHAR(64) PRIMARY KEY,
                caller_id       VARCHAR(128),
                caller_name     VARCHAR(256),
                room_name       VARCHAR(256),
                status          VARCHAR(32) DEFAULT 'active',
                call_start_time TIMESTAMPTZ DEFAULT NOW(),
                call_end_time   TIMESTAMPTZ,
                call_duration_seconds INTEGER,
                is_simulation   BOOLEAN DEFAULT FALSE,
                llm_ttft_ms     INTEGER DEFAULT 0,
                total_latency_ms INTEGER DEFAULT 0
            );
        """)
        # Migrate existing schemas
        await conn.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS is_simulation BOOLEAN DEFAULT FALSE;")
        await conn.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS llm_ttft_ms INTEGER DEFAULT 0;")
        await conn.execute("ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS total_latency_ms INTEGER DEFAULT 0;")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id          SERIAL PRIMARY KEY,
                session_id  VARCHAR(64) NOT NULL REFERENCES call_logs(session_id) ON DELETE CASCADE,
                speaker     VARCHAR(16) NOT NULL,
                message     TEXT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_session ON transcripts(session_id);")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_settings (
                key   VARCHAR(64) PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS call_summaries (
                id              SERIAL PRIMARY KEY,
                session_id      VARCHAR(64) NOT NULL REFERENCES call_logs(session_id) ON DELETE CASCADE,
                summary_text    TEXT NOT NULL,
                call_category   VARCHAR(64) DEFAULT 'Other',
                key_topics      TEXT[],
                action_items    TEXT[],
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        # Seed default settings if empty
        rows = await conn.fetch("SELECT key FROM agent_settings")
        existing_keys = {row['key'] for row in rows}
        defaults = {
            "selected_voice_id": "cartesia:f039066f-cdb7-45ed-b51d-1034ae2f04a0",
            "default_language": "en-IN",
            "agent_name": "AIRA",
            "org_name": "AIRA Solutions",
            "org_description": "We provide premium AI voice receptionist systems.",
            "custom_instructions": "Be polite, helpful, and professional.",
            "business_hours": "9 AM to 5 PM, Monday to Friday",
            "human_escalation": "Transfer to our support line at +1-800-555-0199",
            "topics_to_avoid": "Do not discuss legal advice or product pricing guarantees."
        }
        for k, v in defaults.items():
            if k not in existing_keys:
                await conn.execute("INSERT INTO agent_settings (key, value) VALUES ($1, $2)", k, v)
        logger.info("PostgreSQL database tables verified and seeded successfully")
    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
    finally:
        if conn:
            await conn.close()

# Database Helper Functions
async def fetch_settings() -> dict:
    if not db_pool:
        return {}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT key, value FROM agent_settings")
            return {row['key']: row['value'] for row in rows}
    except Exception as e:
        logger.error("Could not fetch settings from DB: %s", e)
        return {}

async def register_call(session_id: str, caller_phone: str, is_simulation: bool = False) -> None:
    if not db_pool:
        logger.warning("DB offline - cannot register call: %s (phone=%s, simulation=%s)", session_id, caller_phone, is_simulation)
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO call_logs (session_id, caller_id, room_name, status, call_start_time, is_simulation)
                VALUES ($1, $2, $3, $4, NOW(), $5)
                ON CONFLICT (session_id) DO UPDATE SET caller_id = $2, is_simulation = $5
            """, session_id, caller_phone, "mobile_call", "active", is_simulation)
            logger.info("Call registered in DB: %s (phone=%s, is_simulation=%s)", session_id, caller_phone, is_simulation)
    except Exception as e:
        logger.error("Failed to register call in DB %s: %s", session_id, e)

async def persist_caller_name(session_id: str, name: str) -> None:
    if not db_pool:
        logger.warning("DB offline - cannot persist caller name: %s for session: %s", name, session_id)
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE call_logs SET caller_name = $1 WHERE session_id = $2
            """, name, session_id)
            logger.info("Caller name saved in DB: %s (session=%s)", name, session_id)
    except Exception as e:
        logger.warning("Failed to save caller name in DB: %s", e)

async def save_transcript(session_id: str, speaker: str, message: str) -> None:
    if not db_pool:
        logger.warning("DB offline - cannot save transcript for session: %s (speaker=%s)", session_id, speaker)
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO transcripts (session_id, speaker, message)
                VALUES ($1, $2, $3)
            """, session_id, speaker, message)
    except Exception as e:
        logger.warning("Failed to save transcript in DB: %s", e)

async def end_call(session_id: str, avg_ttft: int = 0, avg_total_latency: int = 0) -> None:
    if not db_pool:
        logger.warning("DB offline - cannot end call: %s (avg_ttft=%s, avg_total_latency=%s)", session_id, avg_ttft, avg_total_latency)
        return
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT call_start_time FROM call_logs WHERE session_id = $1", session_id)
            duration = None
            if row and row['call_start_time']:
                start_time = row['call_start_time']
                duration = int((datetime.now(start_time.tzinfo) - start_time).total_seconds())
            await conn.execute("""
                UPDATE call_logs SET status = $1, call_end_time = NOW(), call_duration_seconds = $2, llm_ttft_ms = $3, total_latency_ms = $4
                WHERE session_id = $5
            """, "completed", duration, avg_ttft, avg_total_latency, session_id)
            logger.info("Call ended in DB: %s (duration=%s, avg_ttft=%s, avg_total=%s)", session_id, duration, avg_ttft, avg_total_latency)
            asyncio.create_task(summarize_call_in_db(session_id))
    except Exception as e:
        logger.error("Failed to end call in DB %s: %s", session_id, e)

async def summarize_call_in_db(session_id: str):
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT speaker, message FROM transcripts WHERE session_id = $1 ORDER BY id", session_id)
            if not rows:
                return
            dialog = "\n".join([f"{r['speaker'].upper()}: {r['message']}" for r in rows])
            
            api_key = os.getenv("GOOGLE_API_KEY_AIRA", "")
            if not api_key:
                logger.warning("No GOOGLE_API_KEY for summarization")
                return
            
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            prompt = f"""You are a call summarization assistant. Given a phone call transcript between a caller (USER) and an AI receptionist (AGENT), produce a concise JSON summary.

Return ONLY valid JSON with this structure:
{{
  "summary_text": "2-4 sentence overview of the entire call",
  "call_category": "<one of the categories below>",
  "key_topics": ["topic1", "topic2"],
  "action_items": ["action1", "action2"]
}}

Categories:
- "Product Enquiry": caller asked about a product, service, feature, pricing, or requested a demo
- "Support Request": caller needs help with a problem, issue, or technical matter
- "Billing & Pricing": questions about invoices, payments, costs, or subscriptions
- "Appointment / Booking": caller wants to schedule, reschedule, or cancel a meeting or visit
- "General Information": asking about company hours, location, contact details, or background
- "Complaint": caller is unhappy, raising a complaint, or expressing dissatisfaction
- "Other": anything that doesn't fit the above

Rules:
- summary_text: what the caller wanted and how it was resolved
- key_topics: specific subjects discussed (max 5, concise short phrases). NEVER include caller names, agent names, or phone/contact numbers.
- action_items: any follow-ups needed (empty list if none)

Transcript:
{dialog}"""

            response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            
            res = json.loads(response.text)
            summary_text = res.get("summary_text", "Call ended.")
            call_category = res.get("call_category", "Other")
            key_topics = res.get("key_topics", [])
            action_items = res.get("action_items", [])
            
            # Safe upsert using select-then-update/insert
            exists = await conn.fetchval("SELECT 1 FROM call_summaries WHERE session_id = $1", session_id)
            if exists:
                await conn.execute("""
                    UPDATE call_summaries SET 
                        summary_text = $1,
                        call_category = $2,
                        key_topics = $3,
                        action_items = $4
                    WHERE session_id = $5
                """, summary_text, call_category, key_topics, action_items, session_id)
            else:
                await conn.execute("""
                    INSERT INTO call_summaries (session_id, summary_text, call_category, key_topics, action_items)
                    VALUES ($1, $2, $3, $4, $5)
                """, session_id, summary_text, call_category, key_topics, action_items)
            logger.info("Call summary saved directly to DB for session: %s", session_id)
    except Exception as e:
        logger.error("Failed to generate/save call summary: %s", e)

_USER_NAME_RE = re.compile(
    r"my name(?:'s| is)\s+([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)",
    re.IGNORECASE,
)
_AGENT_NAME_RE = re.compile(
    r"(?:thank(?:s| you)|got it|noted|great)[,!]?\s+([\wऀ-ॿ\u0c00-\u0c7f\u0b80-\u0bff\u0d00-\u0d7f\u0a80-\u0abf\u0b00-\u0b7f]+(?:\s+[\wऀ-ॿ\u0c00-\u0c7f\u0b80-\u0bff\u0d00-\u0d7f\u0a80-\u0abf\u0b00-\u0b7f]+)?)[!,.]",
)
_AGENT_ECHO_NAME_RE = re.compile(
    r"^([\wऀ-ॿ\u0c00-\u0c7f\u0b80-\u0bff\u0d00-\u0d7f\u0a80-\u0abf\u0b00-\u0b7f]{2,20})[,!]\s*(?:ok|sure|noted|got it|ஓகே|சரி)",
    re.IGNORECASE,
)

_LANG_MAP: dict[str, str] = {
    "english": "en-IN", "hindi": "hi-IN", "telugu": "te-IN",
    "tamil": "ta-IN", "kannada": "kn-IN", "malayalam": "ml-IN",
    "తెలుగు": "te-IN", "తెలగు": "te-IN", "తెలేగు": "te-IN",
    "हिंदी": "hi-IN", "हिन्दी": "hi-IN",
    "தமிழ்": "ta-IN", "தெலுகು": "te-IN", "தெலுங்கு": "te-IN",
    "ಕನ್ನಡ": "kn-IN", "ತೆಲುಗು": "te-IN", "ತಮಿಳು": "ta-IN",
    "മലയാളം": "ml-IN",
    "తమిళ్": "ta-IN", "ಕನ್ನಡ": "kn-IN",
    "இந்தி": "hi-IN", "హిందీ": "hi-IN", "ಹಿಂದಿ": "hi-IN",
    "तेलुगु": "te-IN", "तेलगु": "te-IN",
}

_SWITCH_PHRASES = [
    "switch to", "change to", "speak in", "talk in",
    "switch language", "change language", "in english", "in hindi",
    "in telugu", "in tamil", "in kannada", "in malayalam",
]

_KB_FILLERS = ["Sure, let me check...", "One moment...", "Got it, checking...", "Let me look that up..."]

def match_language(text: str) -> str | None:
    lower = text.lower()
    for token, code in _LANG_MAP.items():
        if token in lower or token in text:
            return code
    return None

# 1. Custom Serializer for Raw Audio + Text-based Ping/Pong
class RawFrameSerializer(FrameSerializer):
    def __init__(self):
        super().__init__()
        self.websocket = None

    async def serialize(self, frame: Frame) -> str | bytes | None:
        # Convert outgoing TTS audio frames to raw binary bytes sent over WebSocket
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        elif isinstance(frame, InterruptionFrame):
            return json.dumps({"type": "interrupted"})
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        # If client sends text (e.g. heartbeat ping), handle it directly and send a pong
        if isinstance(data, str):
            if "ping" in data:
                logger.info("Heartbeat ping received, replying with pong")
                if self.websocket:
                    await self.websocket.send_text("pong")
            return None
        
        # If client sends raw audio bytes, return InputAudioRawFrame (16kHz, mono)
        if isinstance(data, bytes):
            return InputAudioRawFrame(audio=data, sample_rate=16000, num_channels=1)
        
        return None


class UserTranscriptInterceptor(FrameProcessor):
    def __init__(self, serializer, get_session_id, context=None, llm=None, agent_interceptor=None, tts=None, stt=None, **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer
        self.get_session_id = get_session_id
        self.context = context
        self.llm = llm
        self.agent_interceptor = agent_interceptor
        self.tts = tts
        self.stt = stt
        self.task = None
        self.agent_name = "AIRA"
        self.org_name = ""
        self.org_description = ""
        self.instructions = ""
        self.current_system_prompt = ""
        self.caller_name_saved = False
        self.language_locked = True
        self.current_language = "en-IN"

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, ErrorFrame):
            logger.error(f"!!! PIPELINE ERROR INTERCEPTED (UserInterceptor) !!! Error: {frame.error} | Fatal: {frame.fatal}")
            
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            # Filter out noise / echo transcripts — too short or empty
            if not text or len(text.strip()) < 4:
                logger.info(f"Dropping noisy transcript: {text!r}")
                return

            logger.info(f"User transcript: {text}")
            sess_id = self.get_session_id()
            asyncio.create_task(save_transcript(sess_id, "user", text))

            # Bulletproof: ensure system prompt is present before every LLM call
            if self.context and self.current_system_prompt:
                has_system = any(m.get("role") == "system" for m in self.context.messages)
                if not has_system:
                    logger.warning("System prompt was missing from context — re-injecting")
                    self.context.messages.insert(0, {"role": "system", "content": self.current_system_prompt})

            # Trim context to system prompt + last 10 messages to avoid 429 rate limits
            if self.context:
                system_msgs = [m for m in self.context.messages if m.get("role") == "system"]
                other_msgs = [m for m in self.context.messages if m.get("role") != "system"]
                if len(other_msgs) > 10:
                    self.context.messages[:] = system_msgs + other_msgs[-10:]
                    logger.debug(f"Context trimmed to {len(self.context.messages)} messages")

            # Broadcast user transcript to the mobile client
            if self.serializer.websocket:
                try:
                    await self.serializer.websocket.send_text(json.dumps({
                        "type": "transcript",
                        "speaker": "user",
                        "text": text
                    }))
                except Exception as e:
                    logger.error(f"Error sending user transcript: {e}")

            # Start timer for TTFT
            if self.agent_interceptor:
                self.agent_interceptor.llm_start_time = asyncio.get_event_loop().time()
                self.agent_interceptor.first_token_received = False

            # Check for user name
            if not self.caller_name_saved:
                m = _USER_NAME_RE.search(text)
                if m:
                    name = m.group(1).strip().title()
                    self.caller_name_saved = True
                    asyncio.create_task(persist_caller_name(sess_id, name))
            
            # Language switching detection
            lower = text.lower()
            detected = match_language(text)
            should_switch = False
            if detected:
                # If we are at the start of the call (first 2 turns) or they use an action keyword
                action_keywords = ["speak", "talk", "switch", "change", "in", "please", "want", "use", "select", "choose"]
                is_start_of_call = (self.context and len(self.context.messages) <= 4)
                if is_start_of_call or any(kw in lower for kw in action_keywords):
                    should_switch = True
                    self.language_locked = True
                        
            if should_switch and detected and detected != self.current_language:
                logger.info(f"Switching language from {self.current_language} to {detected}")
                self.current_language = detected
                # Rebuild and update LLM system instruction
                system_prompt = build_prompt(
                    agent_name=self.agent_name,
                    org_name=self.org_name,
                    language=detected,
                    org_description=self.org_description,
                    instructions=self.instructions
                )
                self.current_system_prompt = system_prompt
                self.llm._settings.system_instruction = system_prompt
                
                # Update system prompt inside LLMContext messages list
                if self.context:
                    system_found = False
                    for msg in self.context.messages:
                        if msg.get("role") == "system":
                            msg["content"] = system_prompt
                            system_found = True
                            break
                    if not system_found:
                        self.context.messages.insert(0, {"role": "system", "content": system_prompt})
                    logger.info("System prompt updated inside LLMContext messages list")
                
                # Update TTS language setting dynamically
                if self.tts:
                    try:
                        asyncio.create_task(self.tts._update_settings(self.tts.Settings(language=detected)))
                        logger.info(f"TTS settings updated to language: {detected}")
                    except Exception as e:
                        logger.error(f"Failed to update TTS language setting: {e}")

                # Update STT language setting dynamically (locks STT to only transcribe target language)
                if self.stt:
                    try:
                        from pipecat.transcriptions.language import Language
                        lang_enum = None
                        for l in Language:
                            if l.value == detected:
                                lang_enum = l
                                break
                        if lang_enum:
                            asyncio.create_task(self.stt._update_settings(self.stt.Settings(language=lang_enum)))
                            logger.info(f"STT settings updated to language: {detected} ({lang_enum})")
                    except Exception as e:
                        logger.error(f"Failed to update STT language setting: {e}")

                # Push a confirmation message bypass LLM
                confirmations = {
                    "hi-IN": "Sure, switching to Hindi now!",
                    "te-IN": "Sure, switching to Telugu now!",
                    "ta-IN": "Sure, switching to Tamil now!",
                    "kn-IN": "Sure, switching to Kannada now!",
                    "ml-IN": "Sure, switching to Malayalam now!",
                    "en-IN": "Sure, switching to English now!"
                }
                phrase = confirmations.get(detected, "Switching language now.")
                if self.task:
                    asyncio.create_task(self.task.queue_frames([TTSSpeakFrame(text=phrase, append_to_context=False)]))
                    
                # Append switch message to LLM context
                if self.context:
                    self.context.add_message({"role": "user", "content": text})
                    self.context.add_message({"role": "assistant", "content": phrase})
                return

        await self.push_frame(frame, direction)


class AgentTranscriptInterceptor(FrameProcessor):
    def __init__(self, serializer, get_session_id, llm, **kwargs):
        super().__init__(**kwargs)
        self.serializer = serializer
        self.get_session_id = get_session_id
        self.llm = llm
        self.user_interceptor = None
        self.current_agent_response = []
        self.llm_start_time = None
        self.first_token_received = True
        self.current_ttft = 0
        self.turn_latencies = []
        self.turn_total_latencies = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, ErrorFrame):
            logger.error(f"!!! PIPELINE ERROR INTERCEPTED (AgentInterceptor) !!! Error: {frame.error} | Fatal: {frame.fatal}")
            
        # Filter out empty or punctuation-only text/speak frames to prevent Sarvam TTS 400 errors
        if isinstance(frame, (TextFrame, TTSSpeakFrame)):
            text = frame.text
            # Only filter out frames that consist entirely of standard English punctuation or whitespace
            if not text or all(c in ".,?!;:()[]{}\"'`~@#$%^&*+-=_|\\/ \t\n\r" for c in text):
                logger.info(f"Filtering out empty/punctuation-only text frame: {text!r}")
                return

        await self.push_frame(frame, direction)
        
        if isinstance(frame, TextFrame):
            self.current_agent_response.append(frame.text)
            
            # Measure TTFT when the first token/text is received from LLM for this turn
            if not self.first_token_received and self.llm_start_time is not None:
                self.first_token_received = True
                self.current_ttft = int((asyncio.get_event_loop().time() - self.llm_start_time) * 1000)
                self.turn_latencies.append(self.current_ttft)
                logger.info(f">>> LATENCY | LLM TTFT: {self.current_ttft}ms <<<")
            
        elif isinstance(frame, LLMFullResponseEndFrame):
            full_text = "".join(self.current_agent_response).strip()
            sess_id = self.get_session_id()
            if full_text:
                logger.info(f"Agent transcript: {full_text}")
                asyncio.create_task(save_transcript(sess_id, "agent", full_text))
                
                # Broadcast agent transcript to the mobile client
                if self.serializer.websocket:
                    try:
                        await self.serializer.websocket.send_text(json.dumps({
                            "type": "transcript",
                            "speaker": "agent",
                            "text": full_text
                        }))
                    except Exception as e:
                        logger.error(f"Error sending agent transcript: {e}")

                # Calculate total turn response generation latency
                total_latency = 0
                if self.llm_start_time is not None:
                    total_latency = int((asyncio.get_event_loop().time() - self.llm_start_time) * 1000)
                    self.turn_total_latencies.append(total_latency)
                    logger.info(f">>> LATENCY | Total Turn: {total_latency}ms | TTFT: {self.current_ttft}ms <<<")

                if self.serializer.websocket:
                    try:
                        # Broadcast latency metrics
                        await self.serializer.websocket.send_text(json.dumps({
                            "type": "metrics",
                            "llm_ttft_ms": self.current_ttft,
                            "total_turn_ms": total_latency
                        }))
                    except Exception as e:
                        logger.error(f"Error sending agent metrics: {e}")

                # Check for agent echoing/saving name
                if self.user_interceptor and not self.user_interceptor.caller_name_saved:
                    m = _AGENT_NAME_RE.search(full_text) or _AGENT_ECHO_NAME_RE.match(full_text)
                    if m:
                        name = m.group(1).strip().title()
                        self.user_interceptor.caller_name_saved = True
                        asyncio.create_task(persist_caller_name(sess_id, name))

            self.current_agent_response = []
            self.current_ttft = 0


_resolved_cartesia_voice_id: str | None = None

async def _resolve_cartesia_voice():
    """Look up 'Ramya' voice ID from Cartesia API at startup."""
    global _resolved_cartesia_voice_id
    env_voice = os.getenv("CARTESIA_VOICE_ID_AIRA", "")
    if env_voice:
        _resolved_cartesia_voice_id = env_voice
        logger.info("Using CARTESIA_VOICE_ID_AIRA from env: %s", env_voice)
        return
    api_key = os.getenv("CARTESIA_API_KEY_AIRA", "")
    if not api_key:
        logger.warning("No CARTESIA_API_KEY_AIRA set, cannot look up Ramya voice")
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.cartesia.ai/voices?q=Ramya&limit=5",
                headers={
                    "X-API-Key": api_key,
                    "Cartesia-Version": "2024-06-10",
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                voices = data if isinstance(data, list) else data.get("data", data.get("voices", []))
                for v in voices:
                    name = v.get("name", "")
                    if "ramya" in name.lower():
                        _resolved_cartesia_voice_id = v["id"]
                        logger.info("Resolved Cartesia voice '%s' → %s", name, v["id"])
                        return
                logger.warning("No 'Ramya' voice found in Cartesia API response. Available: %s",
                               [v.get("name") for v in voices[:5]])
            else:
                logger.warning("Cartesia voice lookup returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Could not look up Cartesia voice: %s", e)

@api_app.on_event("startup")
async def startup_event():
    await init_db()
    await _resolve_cartesia_voice()
    global db_pool
    # Redact password for logging
    safe_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", DATABASE_URL or "")
    logger.info("Attempting DB pool connection to: %s", safe_url[:120])
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, statement_cache_size=0, min_size=1, max_size=5)
        logger.info("PostgreSQL database pool initialized successfully")
    except Exception as e:
        logger.error("!! DB POOL FAILED !! %s: %s", type(e).__name__, e)
        logger.warning("Running DATABASE-LESS. Transcripts, calls, and settings WILL NOT persist. Check DATABASE_URL_AIRA env var on Railway and that Supabase project is not paused.")

@api_app.on_event("shutdown")
async def shutdown_event():
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("PostgreSQL database pool closed successfully")

async def run_pipeline(websocket: WebSocket):
    # Setup custom serializer
    serializer = RawFrameSerializer()

    # Session variables (created per call session)
    session_id = str(uuid.uuid4())
    caller_phone = "+00 00000 00000"

    # Audio params: 16000Hz mono PCM 16-bit
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=16000,
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_10ms_chunks=2,
            serializer=serializer
        )
    )

    # Initialize STT, LLM, TTS services
    stt = SarvamSTTService(
        api_key=os.getenv("SARVAM_API_KEY_AIRA", "dummy_key"),
        model="saarika:v2.5",
        sample_rate=16000
    )
    logger.info("STT provider initialized: Sarvam STT (saarika:v2.5)")
    
    # Dynamic LLM provider selection (Gemini vs Groq)
    llm_provider = os.getenv("LLM_PROVIDER", "").lower()
    groq_key = os.getenv("GROQ_API_KEY_AIRA", "") or os.getenv("GROQ_API_KEY", "")
    gemini_key = os.getenv("GOOGLE_API_KEY_AIRA", "") or os.getenv("GEMINI_API_KEY_AIRA", "") or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")

    if not llm_provider:
        if gemini_key:
            llm_provider = "google"
        else:
            llm_provider = "groq"

    if llm_provider == "google":
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        llm = GoogleLLMService(
            api_key=gemini_key or "dummy_key",
            model=gemini_model,
            settings=GoogleLLMService.Settings(
                max_tokens=120,
                temperature=0.6
            )
        )
        masked_key = f"{gemini_key[:6]}...{gemini_key[-4:]}" if len(gemini_key) > 10 else "None"
        logger.info(f"LLM provider initialized: Google Gemini ({gemini_model}, max_tokens=120) | Active Key: {masked_key}")
    else:
        # Cap responses at ~120 tokens for short, tight replies (per prompt: 2-4 sentences)
        llm_kwargs = {
            "api_key": groq_key or "dummy_key",
            "model": "llama-3.1-8b-instant",
        }
        try:
            from pipecat.services.groq.llm import GroqLLMService as _GLS
            if hasattr(_GLS, "InputParams"):
                llm_kwargs["params"] = _GLS.InputParams(max_tokens=120, temperature=0.6)
        except Exception:
            pass
        llm = GroqLLMService(**llm_kwargs)
        logger.info("LLM provider initialized: Groq (llama-3.1-8b-instant, max_tokens=120)")
    
    sarvam_key = os.getenv("SARVAM_API_KEY_AIRA", "") or os.getenv("SARVAM_API_KEY", "")
    tts = SarvamTTSService(
        api_key=sarvam_key,
        settings=SarvamTTSService.Settings(
            model="bulbul:v3",
            voice="shubh",
            language="en-IN",
            enable_preprocessing=True
        ),
        sample_rate=16000
    )
    logger.info("TTS provider initialized: Sarvam TTS (bulbul:v3, voice_id=shubh)")

    # Configure Context and Aggregators
    context = LLMContext()
    # Start strategy: fire on VAD (immediate) + transcription (fallback), so bot interrupts instantly
    start_strategies = []
    if _VAD_TURN_STRAT_AVAILABLE:
        start_strategies.append(VADUserTurnStartStrategy())
    start_strategies.append(TranscriptionUserTurnStartStrategy())
    user_params = LLMUserAggregatorParams(
        user_turn_strategies=UserTurnStrategies(
            start=start_strategies,
            stop=[ExternalUserTurnStopStrategy(timeout=0.8)]
        )
    )
    context_pair = LLMContextAggregatorPair(context, user_params=user_params)

    # Setup interceptor with None task initially (will assign task after creation)
    get_session_id = lambda: session_id
    agent_interceptor = AgentTranscriptInterceptor(serializer, get_session_id, llm)
    user_interceptor = UserTranscriptInterceptor(serializer, get_session_id, context, llm, agent_interceptor, tts, stt)
    agent_interceptor.user_interceptor = user_interceptor

    # Setup VAD — strict thresholds to reject echo & background noise
    vad = None
    if _VAD_AVAILABLE:
        try:
            vad_params = VADParams(
                confidence=0.85,      # higher = stricter speech detection
                start_secs=0.35,      # need 350ms of speech to start (rejects background noise)
                stop_secs=0.5,        # 500ms of silence to stop
                min_volume=0.8,       # reject quiet ambient/distant sounds
            )
            vad = VADProcessor(vad_analyzer=SileroVADAnalyzer(params=vad_params))
            logger.info("Silero VAD initialized (confidence=0.85, start_secs=0.35, stop_secs=0.5, min_volume=0.8)")
        except Exception as e:
            logger.warning(f"Could not instantiate Silero VAD: {e}")
            vad = None

    # Define Pipecat Pipeline
    pipeline_elements = [transport.input()]
    if vad:
        pipeline_elements.append(vad)
    
    pipeline_elements.extend([
        stt,
        user_interceptor,
        context_pair.user(),
        llm,
        agent_interceptor,
        tts,
        transport.output(),
        context_pair.assistant()
    ])
    
    pipeline = Pipeline(pipeline_elements)
    
    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
    user_interceptor.task = task

    # Implement and Register Knowledge Base Search Tool
    async def search_knowledge_base(params: FunctionCallParams, query: str):
        """Search the company knowledge base to answer caller questions.

        Use this whenever the caller asks about company info, services, pricing,
        hours, FAQs, or anything factual about the organisation.

        Args:
            query: The caller's question or a search phrase derived from it.
        """
        # Play a random filler immediately to mask latency
        phrase = random.choice(_KB_FILLERS)
        await task.queue_frames([TTSSpeakFrame(text=phrase, append_to_context=False)])
        
        lang = user_interceptor.current_language[:2] # e.g. "te" from "te-IN"
        try:
            payload = {"query": query, "k": 2, "language": lang}
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(f"{API_BASE_URL}/knowledge-base/search", json=payload)
                if resp.status_code == 200:
                    docs = resp.json().get("documents", [])
                    if docs:
                        joined = "\n---\n".join(docs)
                        if len(joined) > 600:
                            joined = joined[:600] + "..."
                        await params.result_callback(joined)
                        return
                        
            # Fallback to English search if native language has no docs
            if lang != "en":
                payload = {"query": query, "k": 2, "language": "en"}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(f"{API_BASE_URL}/knowledge-base/search", json=payload)
                    if resp.status_code == 200:
                        docs = resp.json().get("documents", [])
                        if docs:
                            joined = "\n---\n".join(docs)
                            if len(joined) > 600:
                                joined = joined[:600] + "..."
                            await params.result_callback(joined)
                            return
                            
            await params.result_callback("No relevant information found. Tell the caller you'll get someone to follow up.")
        except Exception as e:
            logger.error(f"KB search failed: {e}")
            await params.result_callback("Knowledge base unavailable. Tell the caller you'll get someone to call them back.")

    llm.register_function("search_knowledge_base", search_knowledge_base)

    async def hang_up(params: FunctionCallParams):
        """End the phone call. Call this ONLY when the caller explicitly says goodbye, bye, wants to hang up, or asks to end the call."""
        await task.queue_frames([
            TTSSpeakFrame(text="Goodbye! Have a wonderful day!", append_to_context=False),
            EndFrame()
        ])
        await params.result_callback("Call ended.")

    llm.register_function("hang_up", hang_up)

    # Register event handlers for single client lifecycle
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, websocket_conn):
        nonlocal session_id, caller_phone
        logger.info(f"Client connected: {websocket_conn.client}")
        serializer.websocket = websocket_conn
        
        # Parse query parameters from connection request
        session_id = websocket_conn.query_params.get("session_id") or str(uuid.uuid4())
        caller_phone = websocket_conn.query_params.get("caller_phone") or "+00 00000 00000"
        
        is_simulation = websocket_conn.query_params.get("is_simulation", "false").lower() == "true"
        simulation_prompt = websocket_conn.query_params.get("simulation_prompt", "")
        business_name = websocket_conn.query_params.get("business_name", "")
        agent_name_param = websocket_conn.query_params.get("agent_name", "")
        
        # Register call in database
        asyncio.create_task(register_call(session_id, caller_phone, is_simulation))
        
        # Fetch settings from API
        settings = await fetch_settings()
        agent_name = agent_name_param.strip() if agent_name_param.strip() else settings.get("agent_name", "AIRA")
        org_name = business_name.strip() if business_name.strip() else settings.get("org_name", "")
        org_description = settings.get("org_description", "")
        default_language = settings.get("default_language", "en-IN")
        
        # Build prompt instructions
        instruction_parts = []
        if settings.get("business_hours"):
            instruction_parts.append(f"Business hours: {settings['business_hours']}")
        if settings.get("human_escalation"):
            instruction_parts.append(f"When caller asks for a human: {settings['human_escalation']}")
        if settings.get("topics_to_avoid"):
            instruction_parts.append(f"Do not discuss: {settings['topics_to_avoid']}")
        if settings.get("custom_instructions"):
            instruction_parts.append(settings["custom_instructions"])
            
        if is_simulation and simulation_prompt:
            logger.info("Simulation call detected. Appending simulation custom instructions: %s", simulation_prompt)
            instruction_parts.append(f"\n[CRITICAL SIMULATION SCENARIO / CUSTOM ROLEPLAY INSTRUCTION]:\n{simulation_prompt}")
            
        instructions = "\n".join(instruction_parts)
        
        # Build system prompt using prompts loader
        system_prompt = build_prompt(
            agent_name=agent_name,
            org_name=org_name,
            language=default_language,
            org_description=org_description,
            instructions=instructions
        )
        
        # Set LLM context with system prompt — mutate list in-place to survive property quirks
        try:
            context.messages.clear()
        except Exception:
            pass
        context.add_message({"role": "system", "content": system_prompt})
        
        # Update LLM system instructions
        llm._settings.system_instruction = system_prompt
        logger.info("System prompt set for session %s (%d chars, %d msgs). First 120: %s",
                    session_id, len(system_prompt), len(context.messages), system_prompt[:120])
        
        # Update interceptor settings
        user_interceptor.agent_name = agent_name
        user_interceptor.org_name = org_name
        user_interceptor.org_description = org_description
        user_interceptor.instructions = instructions
        user_interceptor.current_system_prompt = system_prompt
        user_interceptor.current_language = default_language
        user_interceptor.language_locked = True
        user_interceptor.caller_name_saved = False

        # Register mid-call prompt refresh callback for this session
        async def _refresh_prompt(new_settings: dict):
            ns_agent = new_settings.get("agent_name", agent_name)
            ns_org = new_settings.get("org_name", org_name)
            ns_desc = new_settings.get("org_description", org_description)
            parts = []
            if new_settings.get("business_hours"):
                parts.append(f"Business hours: {new_settings['business_hours']}")
            if new_settings.get("human_escalation"):
                parts.append(f"When caller asks for a human: {new_settings['human_escalation']}")
            if new_settings.get("topics_to_avoid"):
                parts.append(f"Do not discuss: {new_settings['topics_to_avoid']}")
            if new_settings.get("custom_instructions"):
                parts.append(new_settings["custom_instructions"])
            if is_simulation and simulation_prompt:
                parts.append(f"\n[CRITICAL SIMULATION SCENARIO / CUSTOM ROLEPLAY INSTRUCTION]:\n{simulation_prompt}")
            new_prompt = build_prompt(
                agent_name=ns_agent,
                org_name=ns_org,
                language=user_interceptor.current_language,
                org_description=ns_desc,
                instructions="\n".join(parts)
            )
            user_interceptor.current_system_prompt = new_prompt
            llm._settings.system_instruction = new_prompt
            updated = False
            for msg in context.messages:
                if msg.get("role") == "system":
                    msg["content"] = new_prompt
                    updated = True
                    break
            if not updated:
                context.messages.insert(0, {"role": "system", "content": new_prompt})
            logger.info("Mid-call system prompt refreshed for session: %s", session_id)

        _session_prompt_updaters[session_id] = _refresh_prompt

        # Play predefined English greeting first so LLM starts call naturally
        greeting = f"Hi, I am {agent_name} from {org_name}. Which language do you want to speak?"
        await task.queue_frames([TTSSpeakFrame(text=greeting, append_to_context=True)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, websocket_conn):
        logger.info("Client disconnected")
        serializer.websocket = None
        _session_prompt_updaters.pop(session_id, None)
        # End call and summarize
        avg_ttft = 0
        if hasattr(agent_interceptor, "turn_latencies") and agent_interceptor.turn_latencies:
            avg_ttft = int(sum(agent_interceptor.turn_latencies) / len(agent_interceptor.turn_latencies))
        avg_total_latency = 0
        if hasattr(agent_interceptor, "turn_total_latencies") and agent_interceptor.turn_total_latencies:
            avg_total_latency = int(sum(agent_interceptor.turn_total_latencies) / len(agent_interceptor.turn_total_latencies))
        asyncio.create_task(end_call(session_id, avg_ttft, avg_total_latency))

    runner = PipelineRunner()
    await runner.add_workers(task)
    
    try:
        await runner.run()
    except Exception as e:
        logger.error(f"Error running pipeline runner: {e}")

@api_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Incoming WebSocket connection accepted on /ws")
    await run_pipeline(websocket)

if __name__ == "__main__":
    port = int(os.getenv("PORT_AIRA", os.getenv("PORT", 8000)))
    logger.info(f"Starting unified backend on port {port}")
    uvicorn.run("main:api_app", host="0.0.0.0", port=port, reload=False)
