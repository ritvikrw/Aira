import logging
import os
import time
import uuid
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from livekit import api as livekit_api

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_PUBLIC_URL = os.getenv("LIVEKIT_PUBLIC_URL", LIVEKIT_URL)


@router.post("/token")
async def create_call_token():
    """Mint a LiveKit room + participant token for a mobile test call.
    Mirrors frontend/src/app/api/livekit/token/route.ts for the Android client."""
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(503, "LiveKit not configured")

    short_id = uuid.uuid4().hex[:8]
    room_name = f"mobile-{short_id}-{int(time.time() * 1000)}"
    participant_identity = f"mobile-caller-{short_id}"

    # Pre-create the room so the agent worker can be dispatched immediately
    lk = livekit_api.LiveKitAPI(LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    try:
        await lk.room.create_room(
            livekit_api.CreateRoomRequest(name=room_name, empty_timeout=300, max_participants=10)
        )
        logger.info("Room created: %s", room_name)
    except Exception:
        # Room may already exist — not fatal
        pass
    finally:
        await lk.aclose()

    token = (
        livekit_api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(participant_identity)
        .with_name("Mobile Caller")
        .with_ttl(timedelta(minutes=15))
        .with_grants(
            livekit_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )
    participant_token = token.to_jwt()
    logger.info("Token generated for room: %s", room_name)

    return {
        "server_url": LIVEKIT_PUBLIC_URL,
        "participant_token": participant_token,
        "room_name": room_name,
    }
