from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import CallLog, CallSummary, Transcript
from services.summarizer import summarize_call

router = APIRouter(prefix="/calls", tags=["calls"])


class CallStartIn(BaseModel):
    session_id: str
    caller_id: str | None = None
    caller_phone: str | None = None
    room_name: str | None = None
    start_time: str | None = None


class CallerInfoIn(BaseModel):
    caller_name: str | None = None


@router.post("/", status_code=201)
async def start_call(body: CallStartIn, db: AsyncSession = Depends(get_db)):
    existing = await db.get(CallLog, body.session_id)
    if existing:
        return {"session_id": existing.session_id, "status": existing.status}
    start_dt = None
    if body.start_time:
        try:
            start_dt = datetime.fromisoformat(body.start_time).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    log = CallLog(
        session_id=body.session_id,
        caller_id=body.caller_id,
        caller_phone=body.caller_phone,
        room_name=body.room_name,
        call_start_time=start_dt or datetime.now(timezone.utc),
    )
    db.add(log)
    await db.commit()
    return {"session_id": log.session_id, "status": "active"}


@router.patch("/{session_id}/caller")
async def update_caller_info(session_id: str, body: CallerInfoIn, db: AsyncSession = Depends(get_db)):
    log = await db.get(CallLog, session_id)
    if not log:
        raise HTTPException(404, "Call not found")
    if body.caller_name is not None:
        log.caller_name = body.caller_name.strip() or None
    await db.commit()
    return {"session_id": session_id, "caller_name": log.caller_name}


@router.post("/{session_id}/end")
async def end_call(session_id: str, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    log = await db.get(CallLog, session_id)
    if not log:
        # Call was never registered (created-on-end flow) — look up room_name from body or just create
        log = CallLog(session_id=session_id, status="ended", call_end_time=now)
        db.add(log)
    else:
        log.call_end_time = now
        log.status = "ended"
        if log.call_start_time:
            log.call_duration_seconds = int((now - log.call_start_time).total_seconds())
    await db.commit()
    return {"session_id": session_id, "duration_seconds": log.call_duration_seconds}


@router.post("/{session_id}/summarize")
async def summarize(session_id: str, db: AsyncSession = Depends(get_db)):
    log = await db.get(CallLog, session_id)
    if not log:
        raise HTTPException(404, "Call not found")

    result = await db.execute(
        select(Transcript)
        .where(Transcript.session_id == session_id)
        .order_by(Transcript.created_at)
    )
    transcripts = [{"speaker": r.speaker, "message": r.message} for r in result.scalars().all()]

    if not transcripts:
        raise HTTPException(422, "No transcripts found for this session")

    summary_data = await summarize_call(transcripts)

    existing = await db.execute(select(CallSummary).where(CallSummary.session_id == session_id))
    existing_row = existing.scalar_one_or_none()

    if existing_row:
        existing_row.summary_text = summary_data["summary_text"]
        existing_row.key_topics = summary_data.get("key_topics", [])
        existing_row.action_items = summary_data.get("action_items", [])
        existing_row.call_category = summary_data.get("call_category", "Other")
    else:
        row = CallSummary(
            session_id=session_id,
            summary_text=summary_data["summary_text"],
            key_topics=summary_data.get("key_topics", []),
            action_items=summary_data.get("action_items", []),
            call_category=summary_data.get("call_category", "Other"),
        )
        db.add(row)

    await db.commit()
    return summary_data


@router.get("/{session_id}")
async def get_call(session_id: str, db: AsyncSession = Depends(get_db)):
    log = await db.get(CallLog, session_id)
    if not log:
        raise HTTPException(404, "Call not found")

    summary_result = await db.execute(
        select(CallSummary).where(CallSummary.session_id == session_id)
    )
    summary = summary_result.scalar_one_or_none()

    return {
        "session_id": log.session_id,
        "caller_id": log.caller_id,
        "caller_name": log.caller_name,
        "caller_phone": log.caller_phone,
        "room_name": log.room_name,
        "status": log.status,
        "call_start_time": log.call_start_time,
        "call_end_time": log.call_end_time,
        "call_duration_seconds": log.call_duration_seconds,
        "summary": {
            "summary_text": summary.summary_text,
            "key_topics": summary.key_topics,
            "action_items": summary.action_items,
            "call_category": summary.call_category,
        } if summary else None,
    }


@router.delete("/all")
async def delete_all_calls(db: AsyncSession = Depends(get_db)):
    """Wipe all call logs, transcripts, and summaries."""
    from sqlalchemy import text
    await db.execute(text("DELETE FROM call_summaries"))
    await db.execute(text("DELETE FROM transcripts"))
    await db.execute(text("DELETE FROM call_logs"))
    await db.commit()
    return {"deleted": True}


@router.post("/cleanup-stale")
async def cleanup_stale_calls_endpoint(
    threshold_minutes: int = 60,
    db: AsyncSession = Depends(get_db),
):
    """Mark any 'active' call older than threshold_minutes as 'ended'.
    Useful for fixing calls that got stuck due to a crash or restart."""
    from sqlalchemy import update
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(CallLog)
        .where(CallLog.status == "active")
        .where(CallLog.call_start_time < cutoff)
        .values(status="ended", call_end_time=now, call_duration_seconds=None)
        .returning(CallLog.session_id)
    )
    fixed = [r[0] for r in result.fetchall()]
    await db.commit()
    logger.info("cleanup-stale: marked %d call(s) as ended: %s", len(fixed), fixed)
    return {"fixed": len(fixed), "session_ids": fixed, "threshold_minutes": threshold_minutes}


@router.post("/recategorize")
async def recategorize_calls(db: AsyncSession = Depends(get_db)):
    """Re-run the summarizer on every call that has transcripts but a missing/null category."""
    # Sessions that have at least one transcript
    tx_result = await db.execute(select(Transcript.session_id).distinct())
    all_tx_sessions = {r[0] for r in tx_result.all()}

    # Sessions already having a proper category
    cat_result = await db.execute(
        select(CallSummary.session_id).where(CallSummary.call_category.isnot(None))
    )
    already_done = {r[0] for r in cat_result.all()}

    to_process = list(all_tx_sessions - already_done)

    processed, failed = 0, 0
    for session_id in to_process:
        try:
            tx_rows = await db.execute(
                select(Transcript).where(Transcript.session_id == session_id).order_by(Transcript.created_at)
            )
            transcripts = [{"speaker": r.speaker, "message": r.message} for r in tx_rows.scalars().all()]
            if not transcripts:
                continue

            summary_data = await summarize_call(transcripts)

            existing = (await db.execute(
                select(CallSummary).where(CallSummary.session_id == session_id)
            )).scalar_one_or_none()

            if existing:
                existing.summary_text = summary_data["summary_text"]
                existing.key_topics = summary_data.get("key_topics", [])
                existing.action_items = summary_data.get("action_items", [])
                existing.call_category = summary_data.get("call_category", "Other")
            else:
                db.add(CallSummary(
                    session_id=session_id,
                    summary_text=summary_data["summary_text"],
                    key_topics=summary_data.get("key_topics", []),
                    action_items=summary_data.get("action_items", []),
                    call_category=summary_data.get("call_category", "Other"),
                ))
            await db.commit()
            processed += 1
        except Exception as e:
            logger.error("Recategorization failed for %s: %s", session_id, e)
            failed += 1

    return {"processed": processed, "failed": failed, "total_needing_update": len(to_process)}


@router.get("/analytics/overview")
async def get_analytics(
    start_date: str | None = None,
    end_date: str | None = None,
    tz: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        local_tz = ZoneInfo(tz) if tz else timezone.utc
    except (ZoneInfoNotFoundError, KeyError):
        local_tz = timezone.utc

    now = datetime.now(local_tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    today_end = today_start + timedelta(days=1)

    # Parse optional date window
    window_start: datetime | None = None
    window_end: datetime | None = None
    if start_date:
        try:
            window_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if end_date:
        try:
            # include the full end day
            window_end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) + timedelta(days=1)
        except ValueError:
            pass

    def _apply_window(q):
        if window_start:
            q = q.where(CallLog.call_start_time >= window_start)
        if window_end:
            q = q.where(CallLog.call_start_time < window_end)
        return q

    # Core counts
    total = await db.scalar(_apply_window(select(func.count(CallLog.session_id)))) or 0
    active = await db.scalar(_apply_window(select(func.count(CallLog.session_id)).where(CallLog.status == "active"))) or 0
    ended = await db.scalar(_apply_window(select(func.count(CallLog.session_id)).where(CallLog.status == "ended"))) or 0
    avg_dur = await db.scalar(_apply_window(
        select(func.avg(CallLog.call_duration_seconds)).where(CallLog.call_duration_seconds.isnot(None))
    ))

    calls_today = await db.scalar(
        select(func.count(CallLog.session_id)).where(CallLog.call_start_time >= today_start)
    ) or 0

    # Daily breakdown — cover the requested window; default to last 30 days if no window
    chart_start = window_start or (now - timedelta(days=30))
    chart_stmt = (
        select(func.date(CallLog.call_start_time).label("date"), func.count(CallLog.session_id).label("count"))
        .where(CallLog.call_start_time >= chart_start)
        .group_by(func.date(CallLog.call_start_time))
        .order_by(func.date(CallLog.call_start_time))
    )
    if window_end:
        chart_stmt = chart_stmt.where(CallLog.call_start_time < window_end)
    daily = [{"date": str(r.date), "count": r.count} for r in (await db.execute(chart_stmt)).all()]

    # Calls by hour — use selected window if provided, else all calls
    hour_q = select(CallLog.call_start_time)
    if window_start:
        hour_q = hour_q.where(CallLog.call_start_time >= window_start)
    if window_end:
        hour_q = hour_q.where(CallLog.call_start_time < window_end)
    hour_map: dict[int, int] = {h: 0 for h in range(0, 24)}
    for t in (await db.execute(hour_q)).scalars().all():
        if t:
            local_hour = t.replace(tzinfo=timezone.utc).astimezone(local_tz).hour
            hour_map[local_hour] += 1
    # Only return hours that have data or span 8am-10pm in local time
    calls_by_hour = [{"hour": h, "count": c} for h, c in sorted(hour_map.items()) if 8 <= h <= 22 or c > 0]

    # Category breakdown
    cat_q = select(CallSummary.call_category).join(CallLog, CallLog.session_id == CallSummary.session_id)
    cat_q = _apply_window(cat_q)
    category_map: dict[str, int] = {}
    for (cat,) in (await db.execute(cat_q)).all():
        category_map[cat or "Other"] = category_map.get(cat or "Other", 0) + 1
    total_cat = sum(category_map.values()) or 1
    categories = sorted(
        [{"name": k, "count": v, "percentage": round(v / total_cat * 100)} for k, v in category_map.items()],
        key=lambda x: -x["count"],
    )

    # Top topics — flatten key_topics arrays across summaries in the window
    topics_q = select(CallSummary.key_topics).join(CallLog, CallLog.session_id == CallSummary.session_id)
    topics_q = _apply_window(topics_q)
    topic_map: dict[str, int] = {}
    for (topics,) in (await db.execute(topics_q)).all():
        for t in (topics or []):
            t = t.strip()
            if t:
                topic_map[t] = topic_map.get(t, 0) + 1
    all_topics = sorted(
        [{"name": k, "count": v} for k, v in topic_map.items()],
        key=lambda x: -x["count"],
    )
    # Use count >= 2 if there are enough recurring topics, else show all
    recurring = [t for t in all_topics if t["count"] >= 2]
    top_topics = (recurring if len(recurring) >= 8 else all_topics)[:25]

    return {
        "total_calls": total,
        "active_calls": active,
        "calls_today": calls_today,
        "avg_duration_seconds": round(avg_dur or 0),
        "calls_last_7_days": daily,
        "calls_by_hour": calls_by_hour,
        "categories": categories,
        "top_topics": top_topics,
        "status_breakdown": {"pending": active, "resolved": ended, "urgent": 0},
    }


@router.get("/")
async def list_calls(room_name: str | None = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import outerjoin as sql_outerjoin
    stmt = (
        select(CallLog, CallSummary.call_category, CallSummary.summary_text, CallSummary.key_topics, CallSummary.action_items)
        .outerjoin(CallSummary, CallLog.session_id == CallSummary.session_id)
        .order_by(CallLog.call_start_time.desc())
        .limit(100)
    )
    if room_name:
        stmt = stmt.where(CallLog.room_name == room_name)
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "session_id": r.CallLog.session_id,
            "caller_id": r.CallLog.caller_id,
            "caller_name": r.CallLog.caller_name,
            "caller_phone": r.CallLog.caller_phone,
            "status": r.CallLog.status,
            "call_start_time": r.CallLog.call_start_time,
            "call_duration_seconds": r.CallLog.call_duration_seconds,
            "room_name": r.CallLog.room_name,
            "call_category": r.call_category,
            "summary_text": r.summary_text,
            "key_topics": r.key_topics or [],
            "action_items": r.action_items or [],
        }
        for r in rows
    ]
