from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AgentSetting

router = APIRouter(prefix="/settings", tags=["settings"])

AVAILABLE_VOICES = [
    # Sarvam AI voices — bulbul:v3 (all Indian languages)
    {"voice_id": "sarvam:ishita",   "name": "Ishita",   "description": "Female, Natural · Sarvam AI"},
    {"voice_id": "sarvam:priya",    "name": "Priya",    "description": "Female, Warm · Sarvam AI"},
    {"voice_id": "sarvam:neha",     "name": "Neha",     "description": "Female, Clear · Sarvam AI"},
    {"voice_id": "sarvam:pooja",    "name": "Pooja",    "description": "Female, Expressive · Sarvam AI"},
    {"voice_id": "sarvam:simran",   "name": "Simran",   "description": "Female, Soft · Sarvam AI"},
    {"voice_id": "sarvam:kavya",    "name": "Kavya",    "description": "Female, Bright · Sarvam AI"},
    {"voice_id": "sarvam:shreya",   "name": "Shreya",   "description": "Female, Confident · Sarvam AI"},
    {"voice_id": "sarvam:tanya",    "name": "Tanya",    "description": "Female, Friendly · Sarvam AI"},
    {"voice_id": "sarvam:shruti",   "name": "Shruti",   "description": "Female, Energetic · Sarvam AI"},
    {"voice_id": "sarvam:suhani",   "name": "Suhani",   "description": "Female, Gentle · Sarvam AI"},
    {"voice_id": "sarvam:ritu",     "name": "Ritu",     "description": "Female, Crisp · Sarvam AI"},
    {"voice_id": "sarvam:roopa",    "name": "Roopa",    "description": "Female, Rich · Sarvam AI"},
    {"voice_id": "sarvam:rupali",   "name": "Rupali",   "description": "Female, Smooth · Sarvam AI"},
    {"voice_id": "sarvam:niharika", "name": "Niharika", "description": "Female, Lively · Sarvam AI"},
    {"voice_id": "sarvam:kavitha",  "name": "Kavitha",  "description": "Female, Deep · Sarvam AI"},
    {"voice_id": "sarvam:rahul",    "name": "Rahul",    "description": "Male, Confident · Sarvam AI"},
    {"voice_id": "sarvam:rohan",    "name": "Rohan",    "description": "Male, Warm · Sarvam AI"},
    {"voice_id": "sarvam:aditya",   "name": "Aditya",   "description": "Male, Natural · Sarvam AI"},
    {"voice_id": "sarvam:ashutosh", "name": "Ashutosh", "description": "Male, Clear · Sarvam AI"},
    {"voice_id": "sarvam:amit",     "name": "Amit",     "description": "Male, Deep · Sarvam AI"},
    {"voice_id": "sarvam:dev",      "name": "Dev",      "description": "Male, Friendly · Sarvam AI"},
    {"voice_id": "sarvam:varun",    "name": "Varun",    "description": "Male, Energetic · Sarvam AI"},
    {"voice_id": "sarvam:kabir",    "name": "Kabir",    "description": "Male, Rich · Sarvam AI"},
    {"voice_id": "sarvam:ratan",    "name": "Ratan",    "description": "Male, Authoritative · Sarvam AI"},
    {"voice_id": "sarvam:manan",    "name": "Manan",    "description": "Male, Crisp · Sarvam AI"},
    {"voice_id": "sarvam:tarun",    "name": "Tarun",    "description": "Male, Smooth · Sarvam AI"},
    {"voice_id": "sarvam:sunny",    "name": "Sunny",    "description": "Male, Bright · Sarvam AI"},
    {"voice_id": "sarvam:mohit",    "name": "Mohit",    "description": "Male, Soft · Sarvam AI"},
    {"voice_id": "sarvam:rehan",    "name": "Rehan",    "description": "Male, Expressive · Sarvam AI"},
    {"voice_id": "sarvam:soham",    "name": "Soham",    "description": "Male, Calm · Sarvam AI"},
    {"voice_id": "sarvam:sumit",    "name": "Sumit",    "description": "Male, Bold · Sarvam AI"},
    {"voice_id": "sarvam:gokul",    "name": "Gokul",    "description": "Male, Grounded · Sarvam AI"},
    {"voice_id": "sarvam:vijay",    "name": "Vijay",    "description": "Male, Strong · Sarvam AI"},
    {"voice_id": "sarvam:advait",   "name": "Advait",   "description": "Male, Measured · Sarvam AI"},
    {"voice_id": "sarvam:anand",    "name": "Anand",    "description": "Male, Warm · Sarvam AI"},
    {"voice_id": "sarvam:aayan",    "name": "Aayan",    "description": "Male, Youthful · Sarvam AI"},
    {"voice_id": "sarvam:shubh",    "name": "Shubh",    "description": "Male, Polished · Sarvam AI"},
    {"voice_id": "sarvam:mani",     "name": "Mani",     "description": "Male, Steady · Sarvam AI"},
    # OpenAI TTS voices
    {"voice_id": "nova",    "name": "Nova",    "description": "Warm, Natural · OpenAI"},
    {"voice_id": "alloy",   "name": "Alloy",   "description": "Neutral, Balanced · OpenAI"},
    {"voice_id": "shimmer", "name": "Shimmer", "description": "Soft, Expressive · OpenAI"},
    {"voice_id": "echo",    "name": "Echo",    "description": "Smooth, Articulate · OpenAI"},
    {"voice_id": "onyx",    "name": "Onyx",    "description": "Deep, Authoritative · OpenAI"},
    # ElevenLabs voices
    {"voice_id": "CwhRBWXzGAHq8TQ4Fs17", "name": "Roger (ElevenLabs)",   "description": "Laid-Back, Casual, Resonant"},
    {"voice_id": "EXAVITQu4vr4xnSDxMaL", "name": "Sarah (ElevenLabs)",   "description": "Mature, Reassuring, Confident"},
    {"voice_id": "FGY2WhTYpPnrIDTdsKH5", "name": "Laura (ElevenLabs)",   "description": "Enthusiast, Quirky Attitude"},
    {"voice_id": "IKne3meq5aSn9XLyUdCD", "name": "Charlie (ElevenLabs)", "description": "Deep, Confident, Energetic"},
    {"voice_id": "JBFqnCBsd6RMkjVDRZzb", "name": "George (ElevenLabs)",  "description": "Warm, Captivating Storyteller"},
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

DEFAULTS = {"selected_voice_id": "sarvam:ishita", "default_language": "en-IN"}


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
