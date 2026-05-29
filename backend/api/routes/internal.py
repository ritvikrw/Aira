from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database import get_db
from models import CallMetrics, CallLog

router = APIRouter(prefix="/internal", tags=["internal"])


class MetricsIn(BaseModel):
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_ttft_ms: Optional[float] = None
    llm_requests: int = 0
    tts_provider: Optional[str] = None
    tts_characters: int = 0
    tts_ttfb_ms: Optional[float] = None
    tts_requests: int = 0
    stt_audio_duration_ms: Optional[float] = None
    stt_ttft_ms: Optional[float] = None
    stt_requests: int = 0


@router.post("/metrics/{session_id}", status_code=201)
async def save_metrics(session_id: str, body: MetricsIn, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(
        select(CallMetrics).where(CallMetrics.session_id == session_id)
    )).scalar_one_or_none()

    if existing:
        existing.llm_prompt_tokens = (existing.llm_prompt_tokens or 0) + body.llm_prompt_tokens
        existing.llm_completion_tokens = (existing.llm_completion_tokens or 0) + body.llm_completion_tokens
        existing.llm_requests = (existing.llm_requests or 0) + body.llm_requests
        existing.tts_characters = (existing.tts_characters or 0) + body.tts_characters
        existing.tts_requests = (existing.tts_requests or 0) + body.tts_requests
        existing.stt_requests = (existing.stt_requests or 0) + body.stt_requests
        existing.stt_audio_duration_ms = (existing.stt_audio_duration_ms or 0) + (body.stt_audio_duration_ms or 0)
        # Keep the first TTFT/TTFB (first response latency is most meaningful)
        if existing.llm_ttft_ms is None and body.llm_ttft_ms is not None:
            existing.llm_ttft_ms = body.llm_ttft_ms
        if existing.tts_ttfb_ms is None and body.tts_ttfb_ms is not None:
            existing.tts_ttfb_ms = body.tts_ttfb_ms
        if existing.stt_ttft_ms is None and body.stt_ttft_ms is not None:
            existing.stt_ttft_ms = body.stt_ttft_ms
        # Save provider name if not set yet
        if existing.tts_provider is None and body.tts_provider:
            existing.tts_provider = body.tts_provider
    else:
        db.add(CallMetrics(session_id=session_id, **body.model_dump()))

    await db.commit()
    return {"ok": True}


@router.get("/metrics")
async def list_metrics(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CallMetrics, CallLog.caller_name, CallLog.caller_id,
               CallLog.call_start_time, CallLog.call_duration_seconds, CallLog.status)
        .outerjoin(CallLog, CallLog.session_id == CallMetrics.session_id)
        .order_by(CallMetrics.created_at.desc())
        .limit(100)
    )
    rows = result.all()
    return [
        {
            "session_id": r.CallMetrics.session_id,
            "caller_name": r.caller_name,
            "caller_id": r.caller_id,
            "call_start_time": str(r.call_start_time) if r.call_start_time else None,
            "call_duration_seconds": r.call_duration_seconds,
            "status": r.status,
            "llm_prompt_tokens": r.CallMetrics.llm_prompt_tokens or 0,
            "llm_completion_tokens": r.CallMetrics.llm_completion_tokens or 0,
            "llm_total_tokens": (r.CallMetrics.llm_prompt_tokens or 0) + (r.CallMetrics.llm_completion_tokens or 0),
            "llm_ttft_ms": round(r.CallMetrics.llm_ttft_ms, 1) if r.CallMetrics.llm_ttft_ms else None,
            "llm_requests": r.CallMetrics.llm_requests or 0,
            "tts_provider": r.CallMetrics.tts_provider or "—",
            "tts_characters": r.CallMetrics.tts_characters or 0,
            "tts_ttfb_ms": round(r.CallMetrics.tts_ttfb_ms, 1) if r.CallMetrics.tts_ttfb_ms else None,
            "tts_requests": r.CallMetrics.tts_requests or 0,
            "stt_audio_duration_ms": round(r.CallMetrics.stt_audio_duration_ms or 0),
            "stt_ttft_ms": round(r.CallMetrics.stt_ttft_ms, 1) if r.CallMetrics.stt_ttft_ms else None,
            "stt_requests": r.CallMetrics.stt_requests or 0,
        }
        for r in rows
    ]


@router.get("/metrics/summary")
async def metrics_summary(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(select(CallMetrics))
    rows = result.scalars().all()
    if not rows:
        return {"total_calls": 0, "avg_llm_ttft_ms": None, "avg_tts_ttfb_ms": None,
                "avg_stt_ttft_ms": None, "total_llm_tokens": 0, "total_tts_characters": 0}

    ttfts  = [r.llm_ttft_ms for r in rows if r.llm_ttft_ms]
    ttfbs  = [r.tts_ttfb_ms for r in rows if r.tts_ttfb_ms]
    sttfts = [r.stt_ttft_ms for r in rows if r.stt_ttft_ms]
    return {
        "total_calls": len(rows),
        "avg_llm_ttft_ms":  round(sum(ttfts)  / len(ttfts),  1) if ttfts  else None,
        "avg_tts_ttfb_ms":  round(sum(ttfbs)  / len(ttfbs),  1) if ttfbs  else None,
        "avg_stt_ttft_ms":  round(sum(sttfts) / len(sttfts), 1) if sttfts else None,
        "total_llm_tokens": sum((r.llm_prompt_tokens or 0) + (r.llm_completion_tokens or 0) for r in rows),
        "total_tts_characters": sum(r.tts_characters or 0 for r in rows),
        "total_stt_duration_ms": round(sum(r.stt_audio_duration_ms or 0 for r in rows)),
    }
