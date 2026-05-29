from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Transcript

router = APIRouter(prefix="/transcripts", tags=["transcripts"])


class TranscriptIn(BaseModel):
    session_id: str
    speaker: str  # 'user' or 'agent'
    message: str


@router.post("/", status_code=201)
async def create_transcript(body: TranscriptIn, db: AsyncSession = Depends(get_db)):
    if body.speaker not in ("user", "agent"):
        raise HTTPException(400, "speaker must be 'user' or 'agent'")
    row = Transcript(session_id=body.session_id, speaker=body.speaker, message=body.message)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "session_id": row.session_id, "speaker": row.speaker}


@router.get("/{session_id}")
async def get_transcripts(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Transcript)
        .where(Transcript.session_id == session_id)
        .order_by(Transcript.created_at)
    )
    rows = result.scalars().all()
    return [
        {"id": r.id, "speaker": r.speaker, "message": r.message, "created_at": r.created_at}
        for r in rows
    ]
