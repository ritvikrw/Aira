import logging
import os
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update

from database import create_tables, AsyncSessionLocal
from models import CallLog
from routes.calls import router as calls_router
from routes.knowledge_base import router as kb_router
from routes.transcripts import router as transcripts_router
from routes.settings import router as settings_router
from routes.internal import router as internal_router
from routes.translate import router as translate_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Calls still "active" after this long are assumed to have crashed without a clean shutdown
STALE_CALL_THRESHOLD_MINUTES = 60


async def cleanup_stale_calls() -> int:
    """Mark any 'active' call older than STALE_CALL_THRESHOLD_MINUTES as 'ended'."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_CALL_THRESHOLD_MINUTES)
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(CallLog)
            .where(CallLog.status == "active")
            .where(CallLog.call_start_time < cutoff)
            .values(
                status="ended",
                call_end_time=now,
                call_duration_seconds=None,   # unknown — process crashed
            )
            .returning(CallLog.session_id)
        )
        fixed = result.fetchall()
        await db.commit()
    if fixed:
        logger.info("Cleaned up %d stale active call(s): %s", len(fixed), [r[0] for r in fixed])
    return len(fixed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("Database tables ready")
    fixed = await cleanup_stale_calls()
    if fixed:
        logger.info("Marked %d stale call(s) as ended on startup", fixed)
    yield


app = FastAPI(title="RECEP API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls_router)
app.include_router(transcripts_router)
app.include_router(kb_router)
app.include_router(settings_router)
app.include_router(internal_router)
app.include_router(translate_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("API_PORT", 8000)), reload=False)
