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
            "agent_name": "Clara",
            "business_name": "Aira Solutions",
            "business_hours": "Monday to Friday, 9am to 6pm IST. Closed on weekends.",
            "agent_instructions": "Answer user queries, explain service offerings, and take callback requests politely.",
            "topics_to_avoid": "Competitor products, ongoing legal matters, internal pricing."
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

@api_app.get("/analytics")
async def get_analytics():
    if not db_pool:
        return {
            "total_calls": 0,
            "today_calls": 0,
            "avg_duration": 0.0,
            "busiest_hour": "N/A",
            "active_calls": 0,
            "volume_over_time": [],
            "calls_by_category": {},
            "top_topics": []
        }
    try:
        async with db_pool.acquire() as conn:
            calls_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*)::integer as total,
                    COUNT(*) FILTER (WHERE call_start_time >= CURRENT_DATE AT TIME ZONE 'Asia/Kolkata')::integer as today
                FROM call_logs
            """)
            total_calls = calls_stats['total'] if calls_stats else 0
            today_calls = calls_stats['today'] if calls_stats else 0

            avg_duration_row = await conn.fetchval("""
                SELECT COALESCE(AVG(call_duration_seconds), 0) FROM call_logs
            """)
            avg_duration = float(avg_duration_row) if avg_duration_row else 0.0

            busiest_hour_row = await conn.fetchrow("""
                SELECT EXTRACT(HOUR FROM call_start_time AT TIME ZONE 'Asia/Kolkata')::integer AS hour, COUNT(*)::integer AS count
                FROM call_logs
                GROUP BY hour
                ORDER BY count DESC, hour ASC
                LIMIT 1
            """)
            if busiest_hour_row:
                h = int(busiest_hour_row['hour'])
                busiest_hour = f"{h:02d}:00"
            else:
                busiest_hour = "N/A"

            active_calls_val = await conn.fetchval("""
                SELECT COUNT(*)::integer FROM call_logs WHERE status = 'active'
            """)
            active_calls = active_calls_val if active_calls_val else 0

            volume_rows = await conn.fetch("""
                SELECT TO_CHAR(call_start_time AT TIME ZONE 'Asia/Kolkata', 'DD Mon') AS day_str, COUNT(*)::integer AS count
                FROM call_logs
                GROUP BY TO_CHAR(call_start_time AT TIME ZONE 'Asia/Kolkata', 'DD Mon'), DATE_TRUNC('day', call_start_time AT TIME ZONE 'Asia/Kolkata')
                ORDER BY DATE_TRUNC('day', call_start_time AT TIME ZONE 'Asia/Kolkata') ASC
                LIMIT 30
            """)
            volume_over_time = [{"label": r['day_str'], "value": r['count']} for r in volume_rows]

            category_rows = await conn.fetch("""
                SELECT call_category, COUNT(*)::integer AS count
                FROM call_summaries
                GROUP BY call_category
                ORDER BY count DESC
            """)
            calls_by_category = {r['call_category']: r['count'] for r in category_rows}

            topic_rows = await conn.fetch("""
                SELECT UNNEST(key_topics) AS topic, COUNT(*)::integer AS count
                FROM call_summaries
                GROUP BY topic
                ORDER BY count DESC
                LIMIT 15
            """)
            top_topics = [{"topic": r['topic'], "count": r['count']} for r in topic_rows if r['topic']]

            return {
                "total_calls": total_calls,
                "today_calls": today_calls,
                "avg_duration": avg_duration,
                "busiest_hour": busiest_hour,
                "active_calls": active_calls,
                "volume_over_time": volume_over_time,
                "calls_by_category": calls_by_category,
                "top_topics": top_topics
            }
    except Exception as e:
        logger.error("API failed to get analytics: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/calls")
async def get_calls():
    if not db_pool:
        return []
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT cl.session_id, cl.caller_id, cl.caller_name, cl.status, 
                       cl.call_start_time, cl.call_end_time, cl.call_duration_seconds, 
                       cl.is_simulation, cl.llm_ttft_ms, cl.total_latency_ms,
                       cs.summary_text, cs.action_needed
                FROM call_logs cl
                LEFT JOIN call_summaries cs ON cl.session_id = cs.session_id
                ORDER BY cl.call_start_time DESC
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
                    "total_latency_ms": r.get('total_latency_ms', 0) if hasattr(r, 'get') else r['total_latency_ms'],
                    "summary_text": r.get('summary_text') or "",
                    "action_needed": r.get('action_needed') or ""
                })
            return calls
    except Exception as e:
        logger.error("API failed to get calls: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_app.get("/calls/{session_id}")
async def get_call_detail(session_id: str):
    if not db_pool:
        raise HTTPException(status_code=404, detail="DB offline")
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT cl.session_id, cl.caller_id, cl.caller_name, cl.status, 
                       cl.call_start_time, cl.call_end_time, cl.call_duration_seconds, 
                       cl.is_simulation, cl.llm_ttft_ms, cl.total_latency_ms,
                       cs.summary_text, cs.action_needed
                FROM call_logs cl
                LEFT JOIN call_summaries cs ON cl.session_id = cs.session_id
                WHERE cl.session_id = $1
            """, session_id)
            if not row:
                raise HTTPException(status_code=404, detail="Call not found")
            return {
                "session_id": row['session_id'],
                "caller_phone": row['caller_id'] or "Unknown",
                "caller_name": row['caller_name'] or "Incoming Call",
                "status": row['status'],
                "call_start_time": row['call_start_time'].isoformat() if row['call_start_time'] else None,
                "call_end_time": row['call_end_time'].isoformat() if row['call_end_time'] else None,
                "call_duration_seconds": row['call_duration_seconds'],
                "is_simulation": row.get('is_simulation', False) if hasattr(row, 'get') else row['is_simulation'],
                "llm_ttft_ms": row.get('llm_ttft_ms', 0) if hasattr(row, 'get') else row['llm_ttft_ms'],
                "total_latency_ms": row.get('total_latency_ms', 0) if hasattr(row, 'get') else row['total_latency_ms'],
                "summary_text": row.get('summary_text') or "",
                "action_needed": row.get('action_needed') or ""
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("API failed to get call detail: %s", e)
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
                action_needed   TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        await conn.execute("ALTER TABLE call_summaries ADD COLUMN IF NOT EXISTS action_needed TEXT;")
        # Seed default settings if empty
        rows = await conn.fetch("SELECT key FROM agent_settings")
        existing_keys = {row['key'] for row in rows}
        defaults = {
            "selected_voice_id": "cartesia:f039066f-cdb7-45ed-b51d-1034ae2f04a0",
            "default_language": "en-IN",
            "agent_name": "Clara",
            "business_name": "Aira Solutions",
            "business_hours": "Monday to Friday, 9am to 6pm IST. Closed on weekends.",
            "agent_instructions": "Answer user queries, explain service offerings, and take callback requests politely.",
            "topics_to_avoid": "Competitor products, ongoing legal matters, internal pricing."
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

from pydantic import BaseModel, Field

class CallSummarySchema(BaseModel):
    summary_text: str = Field(description="A very short, 1-2 sentence overview of the call")
    call_category: str = Field(description="One of the allowed categories: Product Enquiry, Support Request, Billing & Pricing, Appointment / Booking, General Information, Complaint, Other")
    key_topics: list[str] = Field(description="Specific subjects discussed (max 5, concise short phrases). NEVER include caller names, agent names, or phone/contact numbers.")
    action_items: list[str] = Field(description="Any follow-ups needed (empty list if none)")
    action_needed: str | None = Field(default=None, description="A single prominent action statement for the team/owner if the caller requested a callback, follow-up, demo scheduling, or assistance. Otherwise must be set to null or an empty string.")

async def summarize_call_in_db(session_id: str):
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT speaker, message FROM transcripts WHERE session_id = $1 ORDER BY id", session_id)
            if not rows:
                return
            dialog = "\n".join([f"{r['speaker'].upper()}: {r['message']}" for r in rows])
            
            # Fetch business name dynamically for the summarization prompt
            business_name = "Company"
            try:
                biz_row = await conn.fetchrow("SELECT value FROM agent_settings WHERE key = 'business_name'")
                if biz_row and biz_row['value']:
                    business_name = biz_row['value']
            except Exception:
                pass

            api_key = os.getenv("GOOGLE_API_KEY_AIRA", "") or os.getenv("GEMINI_API_KEY_AIRA", "") or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
            if not api_key:
                logger.warning("No GOOGLE_API_KEY for summarization")
                return
            
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            prompt = f"""You are a call summarization assistant. Given a phone call transcript between a caller (USER) and an AI receptionist (AGENT), produce a concise JSON summary.

Categories:
- "Product Enquiry": caller asked about a product, service, feature, pricing, or requested a demo
- "Support Request": caller needs help with a problem, issue, or technical matter
- "Billing & Pricing": questions about invoices, payments, costs, or subscriptions
- "Appointment / Booking": caller wants to schedule, reschedule, or cancel a meeting or visit
- "General Information": asking about company hours, location, contact details, or background
- "Complaint": caller is unhappy, raising a complaint, or expressing dissatisfaction
- "Other": anything that doesn't fit the above

Rules:
- summary_text: Keep it very brief and concise (1-2 sentences maximum). Focus ONLY on the core intent of the caller. If the call was just a brief greeting, background noise, or got disconnected without any actual request or action, make the summary extremely short (e.g., 'The call ended after a brief greeting; no specific request was made.'). Expand only if the caller made a reservation, placed an order, or left an important message to convey to the owner.
- key_topics: specific subjects discussed (max 5, concise short phrases). NEVER include caller names, agent names, or phone/contact numbers.
- action_items: any follow-ups needed (empty list if none)
- action_needed: Critical: If the caller explicitly requested a follow-up, callback, demo scheduling, or left details requiring a company/owner action, extract a single action statement for the team. This must be dynamically generated based on the actual conversation details (such as the caller's name, requested date/time, and target action). Format template: '[Business Name] team to call [Caller Name] at [Time] to [Action]' (e.g. '{business_name} team to call John tomorrow at 2:00 p.m. to schedule a demo'). If details like the caller's name or preferred callback time are not explicitly mentioned in the conversation transcript, use generic placeholders such as 'the caller' or 'as soon as possible' (e.g. '{business_name} team to call the caller as soon as possible to book a large handi') so that the action statement is still successfully created. IMPORTANT: If no follow-up action is required from the company/owner team, set `action_needed` to null or an empty string. Only set it if the team or owner needs to take action based on the call.

Transcript:
{dialog}"""

            gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            response = client.models.generate_content(
                model=gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CallSummarySchema
                ),
            )
            
            res = json.loads(response.text)
            summary_text = res.get("summary_text", "Call ended.")
            call_category = res.get("call_category", "Other")
            key_topics = res.get("key_topics", [])
            action_items = res.get("action_items", [])
            action_needed = res.get("action_needed") or ""
            
            # Safe upsert using select-then-update/insert
            exists = await conn.fetchval("SELECT 1 FROM call_summaries WHERE session_id = $1", session_id)
            if exists:
                await conn.execute("""
                    UPDATE call_summaries SET 
                        summary_text = $1,
                        call_category = $2,
                        key_topics = $3,
                        action_items = $4,
                        action_needed = $5
                    WHERE session_id = $6
                """, summary_text, call_category, key_topics, action_items, action_needed, session_id)
            else:
                await conn.execute("""
                    INSERT INTO call_summaries (session_id, summary_text, call_category, key_topics, action_items, action_needed)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, session_id, summary_text, call_category, key_topics, action_items, action_needed)
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
        self.audio_started = False

    async def serialize(self, frame: Frame) -> str | bytes | None:
        # Convert outgoing TTS audio frames to raw binary bytes sent over WebSocket
        if isinstance(frame, OutputAudioRawFrame):
            if not self.audio_started:
                self.audio_started = True
                logger.info("First audio frame of the turn, sending audio_start signal to client")
                if self.websocket:
                    try:
                        await self.websocket.send_text(json.dumps({"type": "audio_start"}))
                    except Exception as e:
                        logger.error(f"Error sending audio_start signal: {e}")
            return frame.audio
        elif isinstance(frame, InterruptionFrame):
            self.audio_started = False
            return json.dumps({"type": "interrupted"})
        elif type(frame).__name__ == "LLMContextAssistantTurnFrame":
            self.audio_started = False
            return None
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


def get_message_role(msg) -> str:
    # If msg is an LLMSpecificMessage, get its inner message
    if hasattr(msg, "message"):
        msg = msg.message
    # If msg is a dict, get role
    if isinstance(msg, dict):
        return msg.get("role", "")
    # If msg has role attribute (e.g. Google types.Content)
    if hasattr(msg, "role"):
        return msg.role or ""
    return ""

def update_message_content(msg, content: str) -> bool:
    # Unpack LLMSpecificMessage
    is_specific = hasattr(msg, "message")
    inner = msg.message if is_specific else msg
    
    if isinstance(inner, dict):
        inner["content"] = content
        return True
    elif hasattr(inner, "role") and hasattr(inner, "parts"):
        # Google types.Content
        if inner.parts:
            if hasattr(inner.parts[0], "text"):
                inner.parts[0].text = content
            else:
                inner.parts[0] = content
        else:
            inner.parts = [content]
        return True
    return False


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
        self.user_is_speaking = False
        self.speech_detected_in_current_turn = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, ErrorFrame):
            logger.error(f"!!! PIPELINE ERROR INTERCEPTED (UserInterceptor) !!! Error: {frame.error} | Fatal: {frame.fatal}")
            
        # Track VAD speaking state dynamically
        if type(frame).__name__ == "VADUserStartedSpeakingFrame":
            self.user_is_speaking = True
            self.speech_detected_in_current_turn = True
            logger.info("VAD detected user speech started")
        elif type(frame).__name__ == "VADUserStoppedSpeakingFrame":
            self.user_is_speaking = False
            logger.info("VAD detected user speech stopped")

        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            
            # Punctuation-Only Filter: Drop if text is empty or consists entirely of punctuation/whitespace
            clean_text = text.strip()
            if not clean_text or all(c in ".,?!;:()[]{}\"'`~@#$%^&*+-=_|\\/ \t\n\r" for c in clean_text):
                logger.info(f"Dropping empty or punctuation-only transcript: {text!r}")
                return

            # Filler-Word Filter (All Regional Languages)
            normalized_text = clean_text.lower().rstrip(".,?!")
            fillers = {
                "హా", "హ", "हाँ", "हा", "ह", "হ্যাঁ", "হা", "হ", "ஆ", "ആ"
            }
            if normalized_text in fillers:
                logger.info(f"Dropping noise/filler word: {text!r}")
                return

            # Dynamic VAD Check: If VAD indicates user is silent and no speech was detected in this turn, drop it
            if not getattr(self, "user_is_speaking", False) and not getattr(self, "speech_detected_in_current_turn", False):
                logger.info(f"Dropping silence/hum transcription hallucination: {text!r}")
                return
            
            # Reset flag only if the user has finished speaking (VAD is inactive)
            # This ensures multiple transcripts during a single continuous speech turn are all allowed.
            if not getattr(self, "user_is_speaking", False):
                self.speech_detected_in_current_turn = False

            # Language Mismatch Check
            if self.current_language != "en-IN":
                # Check if text is ASCII-only (meaning it's an English transcript hallucinated during a regional call)
                is_pure_english = all(ord(c) < 128 for c in clean_text.replace(".", "").replace("?", "").replace("!", "").strip())
                if is_pure_english:
                    logger.info(f"Dropping English STT hallucination during regional language call: {text!r}")
                    return
            else:
                # English Call Blocklist: Drop known Whisper silence hallucinations
                noise_hallucinations = {
                    "sir, i request you to please sit down",
                    "thank you for watching", "please subscribe"
                }
                if normalized_text in noise_hallucinations:
                    logger.info(f"Dropping English silence hallucination: {text!r}")
                    return

            logger.info(f"User transcript: {text}")
            sess_id = self.get_session_id()
            asyncio.create_task(save_transcript(sess_id, "user", text))

            # Bulletproof: ensure system prompt is present before every LLM call
            if self.context and self.current_system_prompt:
                has_system = any(get_message_role(m) == "system" for m in self.context.messages)
                if not has_system:
                    logger.warning("System prompt was missing from context — re-injecting")
                    self.context.messages.insert(0, {"role": "system", "content": self.current_system_prompt})

            # Trim context to system prompt + last 10 messages to avoid 429 rate limits
            if self.context:
                system_msgs = [m for m in self.context.messages if get_message_role(m) == "system"]
                other_msgs = [m for m in self.context.messages if get_message_role(m) != "system"]
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
                instructions = f"""[BUSINESS HOURS]:
{getattr(self, 'business_hours', '')}

[AGENT INSTRUCTIONS - HOW YOU SHOULD SPEAK]:
{getattr(self, 'agent_instructions', '')}

[TOPICS TO AVOID]:
{getattr(self, 'topics_to_avoid', '')}"""

                from prompts.loader import build_prompt
                system_prompt = build_prompt(
                    agent_name=self.agent_name,
                    org_name=getattr(self, 'business_name', 'Aira Solutions'),
                    language=detected,
                    instructions=instructions
                )
                self.current_system_prompt = system_prompt
                self.llm._settings.system_instruction = system_prompt
                
                # Update system prompt inside LLMContext messages list
                if self.context:
                    system_found = False
                    for msg in self.context.messages:
                        if get_message_role(msg) == "system":
                            update_message_content(msg, system_prompt)
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
                    "hi-IN": "बताइए, आज मैं आपकी कैसे help कर सकता हूँ?",
                    "te-IN": "చెప్పండి, ఈరోజు నేను మీకు ఎలా help చేయగలను?",
                    "ta-IN": "சொல்லுங்க, இன்னைக்கு நான் உங்களுக்கு என்ன help பண்ணட்டும்?",
                    "kn-IN": "ಹೇಳಿ, ಇವತ್ತು ನಾನು ನಿಮಗೆ ಹೇಗೆ help ಮಾಡಬಹುದು?",
                    "ml-IN": "പറയൂ, ഇന്ന് ഞാൻ നിങ്ങൾക്ക് എങ്ങനെയാണ് help ചെയ്യേണ്ടത്?",
                    "en-IN": "How can I help you today?"
                }
                phrase = confirmations.get(detected, "How can I help you today?")
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
            
        elif isinstance(frame, TTSSpeakFrame):
            text = frame.text
            sess_id = self.get_session_id()
            logger.info(f"Agent direct speak transcript: {text}")
            asyncio.create_task(save_transcript(sess_id, "agent", text))
            
            # Broadcast direct speak transcript to client
            if self.serializer.websocket:
                try:
                    await self.serializer.websocket.send_text(json.dumps({
                        "type": "transcript",
                        "speaker": "agent",
                        "text": text
                    }))
                except Exception as e:
                    logger.error(f"Error sending agent direct speak transcript: {e}")

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
        settings=SarvamSTTService.Settings(
            model="saarika:v2.5",
        ),
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
            settings=GoogleLLMService.Settings(
                model=gemini_model,
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
    from pipecat.adapters.schemas.function_schema import FunctionSchema

    context = LLMContext(
        tools=[
            FunctionSchema(
                name="hang_up",
                description="End the phone call. Call this ONLY when the caller explicitly says goodbye, bye, wants to hang up, or asks to end the call.",
                properties={},
                required=[]
            )
        ]
    )
    # Start strategy: fire on VAD (immediate) + transcription (fallback), so bot interrupts instantly
    start_strategies = []
    if _VAD_TURN_STRAT_AVAILABLE:
        start_strategies.append(VADUserTurnStartStrategy())
    start_strategies.append(TranscriptionUserTurnStartStrategy())
    user_params = LLMUserAggregatorParams(
        user_turn_strategies=UserTurnStrategies(
            start=start_strategies,
            stop=[ExternalUserTurnStopStrategy(timeout=1.2)]
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
                confidence=0.85,      # stricter confidence to filter out background speech
                start_secs=0.35,      # require 350ms to verify it's actual speech
                stop_secs=1.2,        # 1.2s of silence to stop (prevents cutting off half-words)
                min_volume=0.25,      # reject background chatter/noise (0.25 is good for direct mouth-mic and normal voice)
            )
            vad = VADProcessor(vad_analyzer=SileroVADAnalyzer(params=vad_params))
            logger.info("Silero VAD initialized (confidence=0.85, start_secs=0.35, stop_secs=1.2, min_volume=0.25)")
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


    async def hang_up(params: FunctionCallParams):
        """End the phone call. Call this ONLY when the caller explicitly says goodbye, bye, wants to hang up, or asks to end the call."""
        lang = user_interceptor.current_language if hasattr(user_interceptor, "current_language") else "en-IN"
        goodbyes = {
            "en-IN": "Goodbye! Have a wonderful day!",
            "te-IN": "సరేనండి, సెలవు! మీ రోజు చాలా బాగుండాలని కోరుకుంటున్నాను!",
            "hi-IN": "अलविदा! आपका दिन शुभ हो!",
            "ta-IN": "சரிங்க, பாய்! இந்த நாள் உங்களுக்கு நல்லா இருக்கட்டும்!",
            "kn-IN": "ಹೋಗಿ ಬರ್ತೀನಿ! ನಿಮ್ಮ ದಿನ ಒಳ್ಳೆಯದಾಗಿರಲಿ!",
            "ml-IN": "പോയി വരാം! നല്ലൊരു ദിവസം ആശംസിക്കുന്നു!"
        }
        goodbye_text = goodbyes.get(lang, "Goodbye! Have a wonderful day!")
        await task.queue_frames([
            TTSSpeakFrame(text=goodbye_text, append_to_context=False),
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
        business_name_param = websocket_conn.query_params.get("business_name", "")
        agent_name_param = websocket_conn.query_params.get("agent_name", "")
        
        # Register call in database
        asyncio.create_task(register_call(session_id, caller_phone, is_simulation))
        
        # Fetch settings from API
        settings = await fetch_settings()
        agent_name = agent_name_param.strip() if agent_name_param.strip() else settings.get("agent_name", "Clara")
        business_name_val = business_name_param.strip() if business_name_param.strip() else settings.get("business_name", "Aira Solutions")
        business_hours = settings.get("business_hours", "Monday to Friday, 9am to 6pm IST. Closed on weekends.")
        agent_instructions = settings.get("agent_instructions", "Answer user queries, explain service offerings, and take callback requests politely.")
        topics_to_avoid = settings.get("topics_to_avoid", "Competitor products, ongoing legal matters, internal pricing.")
        default_language = settings.get("default_language", "en-IN")
        
        # If in simulation mode, append simulation custom instructions
        if is_simulation and simulation_prompt:
            logger.info("Simulation call detected. Appending simulation custom instructions: %s", simulation_prompt)
            agent_instructions += f"\n\n[CRITICAL SIMULATION SCENARIO / CUSTOM ROLEPLAY INSTRUCTION]:\n{simulation_prompt}"
            
        # Build system prompt using structured format
        instructions = f"""[BUSINESS HOURS]:
{business_hours}

[AGENT INSTRUCTIONS - HOW YOU SHOULD SPEAK]:
{agent_instructions}

[TOPICS TO AVOID]:
{topics_to_avoid}"""

        from prompts.loader import build_prompt
        system_prompt = build_prompt(
            agent_name=agent_name,
            org_name=business_name_val,
            language=default_language,
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
        user_interceptor.business_name = business_name_val
        user_interceptor.business_hours = business_hours
        user_interceptor.agent_instructions = agent_instructions
        user_interceptor.topics_to_avoid = topics_to_avoid
        user_interceptor.current_system_prompt = system_prompt
        user_interceptor.current_language = default_language
        user_interceptor.language_locked = True
        user_interceptor.caller_name_saved = False

        # Register mid-call prompt refresh callback for this session
        async def _refresh_prompt(new_settings: dict):
            ns_agent = new_settings.get("agent_name", agent_name)
            ns_business = new_settings.get("business_name", business_name_val)
            ns_hours = new_settings.get("business_hours", business_hours)
            ns_instructions = new_settings.get("agent_instructions", agent_instructions)
            ns_avoid = new_settings.get("topics_to_avoid", topics_to_avoid)
            
            if is_simulation and simulation_prompt:
                ns_instructions += f"\n\n[CRITICAL SIMULATION SCENARIO / CUSTOM ROLEPLAY INSTRUCTION]:\n{simulation_prompt}"
                
            ns_instructions_block = f"""[BUSINESS HOURS]:
{ns_hours}

[AGENT INSTRUCTIONS - HOW YOU SHOULD SPEAK]:
{ns_instructions}

[TOPICS TO AVOID]:
{ns_avoid}"""

            from prompts.loader import build_prompt
            new_prompt = build_prompt(
                agent_name=ns_agent,
                org_name=ns_business,
                language=user_interceptor.current_language,
                instructions=ns_instructions_block
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

        # Update TTS and STT settings to use the selected default language on startup
        if tts:
            try:
                await tts._update_settings(tts.Settings(language=default_language))
                logger.info(f"TTS language initialized to default: {default_language}")
            except Exception as e:
                logger.error(f"Failed to update TTS language setting at startup: {e}")
                
        if stt:
            try:
                from pipecat.transcriptions.language import Language
                lang_enum = None
                for l in Language:
                    if l.value == default_language:
                        lang_enum = l
                        break
                if lang_enum:
                    await stt._update_settings(stt.Settings(language=lang_enum))
                    logger.info(f"STT language initialized to default: {default_language} ({lang_enum})")
            except Exception as e:
                logger.error(f"Failed to update STT language setting at startup: {e}")

        # Play predefined greeting first in the chosen default language so LLM starts call naturally
        greetings = {
            "en-IN": f"Hi, I am {agent_name} from {business_name_val}. Which language do you want to speak?",
            "te-IN": f"నమస్కారం, నేను {business_name_val} నుండి {agent_name} ని. మీరు ఏ భాషలో మాట్లాడాలనుకుంటున్నారు?",
            "hi-IN": f"नमस्ते, मैं {business_name_val} से {agent_name} हूँ। आप किस भाषा में बात करना चाहते हैं?",
            "ta-IN": f"வணக்கம், நான் {business_name_val}-லிருந்து {agent_name} பேசறேன். நீங்க எந்த மொழியில பேச விரும்புறீங்க?",
            "kn-IN": f"ನಮಸ್ಕಾರ, ನಾನು {business_name_val} ಇಂದ {agent_name}. ನೀವು ಯಾವ ಭಾಷೆಯಲ್ಲಿ ಮಾತನಾಡಲು ಬಯಸುತ್ತೀರಿ?",
            "ml-IN": f"നമസ്കാരം, ഞാൻ {business_name_val}-ൽ നിന്ന് {agent_name} ആണ്. നിങ്ങൾക്ക് ഏത് ഭാഷയിലാണ് സംസാരിക്കേണ്ടത്?"
        }
        greeting = greetings.get(default_language, greetings["en-IN"])
        await task.queue_frames([TTSSpeakFrame(text=greeting, append_to_context=True)])

    call_ended_triggered = False

    async def trigger_end_call():
        nonlocal call_ended_triggered
        if call_ended_triggered:
            return
        call_ended_triggered = True
        avg_ttft = 0
        if hasattr(agent_interceptor, "turn_latencies") and agent_interceptor.turn_latencies:
            avg_ttft = int(sum(agent_interceptor.turn_latencies) / len(agent_interceptor.turn_latencies))
        avg_total_latency = 0
        if hasattr(agent_interceptor, "turn_total_latencies") and agent_interceptor.turn_total_latencies:
            avg_total_latency = int(sum(agent_interceptor.turn_total_latencies) / len(agent_interceptor.turn_total_latencies))
        await end_call(session_id, avg_ttft, avg_total_latency)

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, websocket_conn):
        logger.info("Client disconnected")
        serializer.websocket = None
        _session_prompt_updaters.pop(session_id, None)
        # End call and summarize
        asyncio.create_task(trigger_end_call())

    runner = PipelineRunner()
    await runner.add_workers(task)
    
    try:
        await runner.run()
    except Exception as e:
        logger.error(f"Error running pipeline runner: {e}")
    finally:
        await trigger_end_call()

@api_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Incoming WebSocket connection accepted on /ws")
    await run_pipeline(websocket)

if __name__ == "__main__":
    port = int(os.getenv("PORT_AIRA", os.getenv("PORT", 8000)))
    logger.info(f"Starting unified backend on port {port}")
    uvicorn.run("main:api_app", host="0.0.0.0", port=port, reload=False)
