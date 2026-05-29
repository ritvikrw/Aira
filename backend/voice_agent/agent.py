import asyncio
import logging
import os
import re

import httpx
from livekit.agents import Agent

_api_client = httpx.AsyncClient(timeout=5.0)

from prompts import build_system_prompt
from tools import _persist_caller_name, search_knowledge_base

# Matches "my name is X" / "my name's X" — safe, low false-positive rate
_USER_NAME_RE = re.compile(
    r"my name(?:'s| is)\s+([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)",
    re.IGNORECASE,
)
# Matches agent acknowledgement "Thank you, X!" / "Got it, X." — catches remaining cases
_AGENT_NAME_RE = re.compile(
    r"(?:thank(?:s| you)|got it|noted|great)[,!]?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[!,.]",
)

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

_GREETINGS: dict[str, str] = {
    "en-IN": "Hey, thanks for calling {org}, this is {name}. How can I help?",
    "hi-IN": "हेलो! {org} में call करने के लिए thanks. मेरा नाम {name} है. कैसे help करूं?",
    "ta-IN": "வணக்கம்! {org} call பண்ணதுக்கு thanks. என் பேரு {name}. எப்படி help பண்ணலாம்?",
    "te-IN": "నమస్కారం! {org} కి call చేసినందుకు thanks. నా పేరు {name}. ఎలా help చేయాలి?",
    "kn-IN": "ನಮಸ್ಕಾರ! {org} ಗೆ call ಮಾಡಿದ್ದಕ್ಕೆ thanks. ನನ್ನ ಹೆಸರು {name}. ಹೇಗೆ help ಮಾಡಲಿ?",
    "ml-IN": "നമസ്കാരം! {org} ൽ call ചെയ്തതിന് thanks. എന്റെ പേര് {name}. എങ്ങനെ help ചെയ്യാം?",
    "mr-IN": "नमस्कार! {org} ला call केल्याबद्दल thanks. माझं नाव {name} आहे. कसं help करू?",
    "bn-IN": "নমস্কার! {org}-এ call করার জন্য thanks. আমার নাম {name}. কীভাবে help করতে পারি?",
    "gu-IN": "નમસ્તે! {org} ને call કર્યા બદલ thanks. મારું નામ {name} છે. કેવી રીતે help કરું?",
    "pa-IN": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! {org} ਨੂੰ call ਕਰਨ ਲਈ thanks. ਮੇਰਾ ਨਾਮ {name} ਹੈ. ਕਿਵੇਂ help ਕਰਾਂ?",
}


class ReceptionistAgent(Agent):
    def __init__(
        self,
        session_id: str,
        agent_name: str = "aira",
        org_name: str = "",
        org_description: str = "",
        instructions: str = "",
        default_language: str = "en-IN",
    ):
        super().__init__(
            instructions=build_system_prompt(
                agent_name, org_name, org_description, instructions, default_language
            ),
            tools=[search_knowledge_base],
        )
        self._session_id       = session_id
        self._agent_name       = agent_name
        self._org_name         = org_name
        self._default_language = default_language
        self._caller_name_saved = False   # prevent duplicate PATCHes

    async def on_enter(self) -> None:
        if self._default_language and self._default_language != "en-IN":
            template = _GREETINGS.get(self._default_language, _GREETINGS["en-IN"])
            greeting = template.format(org=self._org_name, name=self._agent_name)
        else:
            # Just greet naturally — Sarvam STT auto-detects whatever language
            # the caller responds in, no need to ask them to choose.
            greeting = (
                f"Hey, thanks for calling {self._org_name}, this is {self._agent_name}! "
                f"How can I help you today?"
            )
        await self.session.say(greeting)

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = getattr(new_message, "text_content", None)
        if text:
            asyncio.create_task(_save_transcript(self._session_id, "user", text))
            # Detect caller name from "my name is X" without a tool-call round trip
            if not self._caller_name_saved:
                m = _USER_NAME_RE.search(text)
                if m:
                    name = m.group(1).strip().title()
                    self._caller_name_saved = True
                    logger.info("Detected caller name from user message: %s", name)
                    asyncio.create_task(_persist_caller_name(self._session_id, name))

    def on_agent_reply(self, text: str) -> None:
        """Called from main.py after each assistant turn to catch names the agent acknowledged."""
        if not self._caller_name_saved and text:
            m = _AGENT_NAME_RE.search(text)
            if m:
                name = m.group(1).strip().title()
                self._caller_name_saved = True
                logger.info("Detected caller name from agent reply: %s", name)
                asyncio.create_task(_persist_caller_name(self._session_id, name))


async def _save_transcript(session_id: str, speaker: str, message: str) -> None:
    try:
        await _api_client.post(
            f"{API_BASE_URL}/transcripts/",
            json={"session_id": session_id, "speaker": speaker, "message": message},
        )
    except Exception as e:
        logger.warning("Failed to save transcript (session=%s): %s", session_id, e)


async def end_call(
    session_id: str,
    room_name: str | None = None,
    caller_id: str | None = None,
    start_time: str | None = None,
) -> None:
    try:
        await _api_client.post(
            f"{API_BASE_URL}/calls/",
            json={"session_id": session_id, "room_name": room_name,
                  "caller_id": caller_id, "start_time": start_time},
            timeout=10.0,
        )
        await _api_client.post(f"{API_BASE_URL}/calls/{session_id}/end", timeout=10.0)
        await _api_client.post(f"{API_BASE_URL}/calls/{session_id}/summarize", timeout=30.0)
        logger.info("Call ended and summarized: %s", session_id)
    except Exception as e:
        logger.error("Failed to end/summarize call %s: %s", session_id, e)
