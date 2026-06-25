from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AgentSetting

router = APIRouter(prefix="/settings", tags=["settings"])

AVAILABLE_VOICES = [
    # ── Cartesia Sonic-3 — all languages, ~90ms latency ──────────────────────
    # English
    {"voice_id": "cartesia:f8f5f1b2-f02d-4d8e-a40d-fd850a487b3d", "name": "Kiara",  "description": "Indian-accented English, upbeat · Cartesia"},
    {"voice_id": "cartesia:f039066f-cdb7-45ed-b51d-1034ae2f04a0", "name": "Cindy",  "description": "Smooth, welcoming receptionist · Cartesia"},
    {"voice_id": "cartesia:a7a59115-2425-4192-844c-1e98ec7d6877", "name": "Amber",  "description": "Warm support agent · Cartesia"},
    {"voice_id": "cartesia:d46abd1d-2d02-43e8-819f-51fb652c1c61", "name": "Grant",  "description": "Reliable, clear male · Cartesia"},
    # Hindi
    {"voice_id": "cartesia:56e35e2d-6eb6-4226-ab8b-9776515a7094", "name": "Kavita", "description": "Customer care, mature female · Cartesia Hindi"},
    {"voice_id": "cartesia:bec003e2-3cb3-429c-8468-206a393c67ad", "name": "Parvati","description": "Friendly supporter · Cartesia Hindi"},
    {"voice_id": "cartesia:47f3bbb1-e98f-4e0c-92c5-5f0325e1e206", "name": "Neha",   "description": "Virtual assistant, composed · Cartesia Hindi"},
    # Telugu
    {"voice_id": "cartesia:cf061d8b-a752-4865-81a2-57570a6e0565", "name": "Ramya",  "description": "Graceful host, warm · Cartesia Telugu"},
    {"voice_id": "cartesia:4418bb06-8329-49a1-bb11-53bb64ca0547", "name": "Shanti", "description": "Calm authority · Cartesia Telugu"},
    # Tamil
    {"voice_id": "cartesia:7f98e662-142d-41ba-89a2-12452640ce6d", "name": "Lakshmi", "description": "Casual, upbeat female · Cartesia Tamil"},
    {"voice_id": "cartesia:25d2c432-139c-4035-bfd6-9baaabcdd006", "name": "Kavya",   "description": "Warm presence · Cartesia Tamil"},
    {"voice_id": "cartesia:01d7796d-ac10-4ea3-8df0-3cc04f2d25ff", "name": "Kavitha", "description": "Clear communicator · Cartesia Tamil"},
    # Kannada
    {"voice_id": "cartesia:7c6219d2-e8d2-462c-89d8-7ecba7c75d65", "name": "Divya",  "description": "Joyful narrator · Cartesia Kannada"},
    # Malayalam
    {"voice_id": "cartesia:b426013c-002b-4e89-8874-8cd20b68373a", "name": "Latha",  "description": "Friendly host · Cartesia Malayalam"},
    # ── OpenAI TTS ────────────────────────────────────────────────────────────
    {"voice_id": "nova",    "name": "Nova",    "description": "Warm, Natural · OpenAI"},
    {"voice_id": "alloy",   "name": "Alloy",   "description": "Neutral, Balanced · OpenAI"},
    {"voice_id": "shimmer", "name": "Shimmer", "description": "Soft, Expressive · OpenAI"},
    {"voice_id": "echo",    "name": "Echo",    "description": "Smooth, Articulate · OpenAI"},
    {"voice_id": "onyx",    "name": "Onyx",    "description": "Deep, Authoritative · OpenAI"},
    {"voice_id": "ash",     "name": "Ash",     "description": "Crisp, Confident · OpenAI"},
    {"voice_id": "sage",    "name": "Sage",    "description": "Calm, Thoughtful · OpenAI"},
    {"voice_id": "coral",   "name": "Coral",   "description": "Friendly, Clear · OpenAI"},
]

AVAILABLE_LANGUAGES = [
    {"code": "en-IN", "name": "English"},
    {"code": "hi-IN", "name": "Hindi"},
    {"code": "ta-IN", "name": "Tamil"},
    {"code": "te-IN", "name": "Telugu"},
    {"code": "kn-IN", "name": "Kannada"},
    {"code": "ml-IN", "name": "Malayalam"},
    {"code": "mr-IN", "name": "Marathi"},
    {"code": "bn-IN", "name": "Bengali"},
    {"code": "gu-IN", "name": "Gujarati"},
    {"code": "pa-IN", "name": "Punjabi"},
]

DEFAULTS = {"selected_voice_id": "cartesia:f039066f-cdb7-45ed-b51d-1034ae2f04a0", "default_language": "en-IN"}


async def _read_all(db: AsyncSession) -> dict:
    result = await db.execute(select(AgentSetting))
    rows = result.scalars().all()
    data = DEFAULTS.copy()
    for row in rows:
        data[row.key] = row.value
    return data


@router.get("/voices")
def list_voices():
    return AVAILABLE_VOICES


@router.get("/languages")
def list_languages():
    return AVAILABLE_LANGUAGES


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await _read_all(db)


@router.post("")
async def update_settings(body: dict, db: AsyncSession = Depends(get_db)):
    for key, value in body.items():
        existing = await db.get(AgentSetting, key)
        if existing:
            existing.value = str(value)
        else:
            db.add(AgentSetting(key=key, value=str(value)))
    await db.commit()
    return await _read_all(db)
