import asyncio
import logging
import os
import re

import httpx
from livekit.agents import Agent

_api_client = httpx.AsyncClient(timeout=5.0)

from prompts import build_system_prompt, build_locked_prompt
from tools import _persist_caller_name, search_knowledge_base


_USER_NAME_RE = re.compile(
    r"my name(?:'s| is)\s+([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z]+)?)",
    re.IGNORECASE,
)
_AGENT_NAME_RE = re.compile(
    r"(?:thank(?:s| you)|got it|noted|great)[,!]?\s+([\wऀ-ॿఀ-౿஀-௿ഀ-ൿ઀-૿଀-୿]+(?:\s+[\wऀ-ॿఀ-౿஀-௿ഀ-ൿ઀-૿଀-୿]+)?)[!,.]",
)
# Matches agent echoing name at start: "Mani, ok" / "மணி, ok" / "Sure Priya,"
_AGENT_ECHO_NAME_RE = re.compile(
    r"^([\wऀ-ॿఀ-౿஀-௿ഀ-ൿ઀-૿଀-୿]{2,20})[,!]\s*(?:ok|sure|noted|got it|ஓகே|சரி)",
    re.IGNORECASE,
)

_LANG_MAP: dict[str, str] = {
    "english": "en-IN", "hindi": "hi-IN", "telugu": "te-IN",
    "tamil": "ta-IN", "kannada": "kn-IN", "malayalam": "ml-IN",
    "marathi": "mr-IN", "bengali": "bn-IN", "gujarati": "gu-IN", "punjabi": "pa-IN",
    "తెలుగు": "te-IN", "తెలగు": "te-IN",
    "हिंदी": "hi-IN", "हिन्दी": "hi-IN",
    "தமிழ்": "ta-IN",
    "ಕನ್ನಡ": "kn-IN",
    "മലയാളം": "ml-IN",
    "मराठी": "mr-IN",
    "বাংলা": "bn-IN",
    "ਪੰਜਾਬੀ": "pa-IN",
    "ਤੇਲਗੂ": "te-IN", "ਤੇਲੁਗੂ": "te-IN",
    "తెలేగు": "te-IN", "తెలుగు": "te-IN",
    "तेलुगु": "te-IN", "तेलगु": "te-IN",
    "ତେଲୁଗୁ": "te-IN", "ତେଲକୁ": "te-IN",
    "தெலுகு": "te-IN", "தெலுங்கு": "te-IN", "தெலுகூ": "te-IN",
    "ತೆಲುಗು": "te-IN", "ತೆಲಗು": "te-IN",
    "இந்தி": "hi-IN", "హిందీ": "hi-IN", "ಹಿಂದಿ": "hi-IN",
    "తమిళ్": "ta-IN", "ತಮಿಳು": "ta-IN",
    "కన్నడ": "kn-IN", "கன்னடம்": "kn-IN",
}

_SWITCH_PHRASES = [
    "switch to", "change to", "speak in", "talk in",
    "switch language", "change language", "in english", "in hindi",
    "in telugu", "in tamil", "in kannada", "in malayalam",
]

# Thinking fillers — short, natural bridging phrases
_THINKING_FILLERS = ["Sure...", "One moment...", "Got it...", "Let me check..."]
_filler_index = 0

# Language-switch filler — English, plays before language is locked
_LANG_SWITCH_FILLER = "Sure, switching now!"

# Silence check phrases per language
_SILENCE_PHRASES = {
    "te-IN": "నేను ఇక్కడే ఉన్నాను, మీరు వినగలుగుతున్నారా?",
    "hi-IN": "main yahan hoon, kya aap sun pa rahe hain?",
    "ta-IN": "naan inge irukkiren, kekkuringala?",
    "kn-IN": "naanu illiddeene, neevu keluttiddeera?",
    "ml-IN": "njaan ivideyundu, kelkkunundo?",
    "en-IN": "I'm still here, are you there?",
}

# One-line native greetings for non-English default languages.
_NATIVE_GREETINGS: dict[str, str] = {
    "te-IN": "నమస్కారం! నేను {name}, {org} నుండి మాట్లాడుతున్నాను — మీకు ఎలా help చేయగలను?",
    "ta-IN": "வணக்கம்! நான் {name}, {org}-ல இருந்து பேசறேன் — எப்படி help பண்ணலாம்?",
    "kn-IN": "ನಮಸ್ಕಾರ! ನಾನು {name}, {org} ಕಡೆಯಿಂದ ಮಾತನಾಡುತ್ತಿದ್ದೇನೆ — ಹೇಗೆ help ಮಾಡಬಹುದು?",
    "hi-IN": "नमस्ते! मैं {name} हूँ, {org} की तरफ से — आपकी कैसे help कर सकती हूँ?",
    "ml-IN": "നമസ്കാരം! ഞാൻ {name}, {org}-ൽ നിന്ന് — എങ്ങനെ help ചെയ്യാം?",
    "mr-IN": "नमस्कार! मी {name}, {org} कडून बोलतेय — कशी मदत करू?",
    "bn-IN": "নমস্কার! আমি {name}, {org} থেকে বলছি — কীভাবে সাহায্য করতে পারি?",
    "gu-IN": "નમસ્તે! હું {name}, {org} તરફથી — કઈ રીતે help કરી શકું?",
    "pa-IN": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ {name}, {org} ਤੋਂ — ਕਿਵੇਂ help ਕਰ ਸਕਦੀ ਹਾਂ?",
}

logger = logging.getLogger(__name__)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class ReceptionistAgent(Agent):
    def __init__(self, session_id, agent_name="aira", org_name="",
                 org_description="", instructions="", default_language="en-IN"):
        super().__init__(
            instructions=build_system_prompt(agent_name, org_name, org_description, instructions, default_language),
            tools=[search_knowledge_base],
        )
        self._session_id        = session_id
        self._agent_name        = agent_name
        self._org_name          = org_name
        self._default_language  = default_language
        self._org_description   = org_description
        self._instructions_str  = instructions
        self._caller_name_saved = False
        self._first_turn_done   = False
        self._silence_task: asyncio.Task | None = None
        self._filler_task: asyncio.Task | None = None

        try:
            import sarvam_stt
            sarvam_stt.reset_language()
        except ImportError:
            pass

    async def on_enter(self) -> None:
        if self._default_language != "en-IN" and self._default_language in _NATIVE_GREETINGS:
            greeting = _NATIVE_GREETINGS[self._default_language].format(
                name=self._agent_name, org=self._org_name
            )
        else:
            greeting = (
                f"Hi, this is {self._agent_name} from {self._org_name}! "
                f"Which language would you like to speak in?"
            )
        await self.session.say(greeting)

    # ------------------------------------------------------------------
    # Silence detection
    # ------------------------------------------------------------------

    def _cancel_silence_timer(self) -> None:
        if self._silence_task and not self._silence_task.done():
            self._silence_task.cancel()
            self._silence_task = None

    def _start_silence_timer(self) -> None:
        self._cancel_silence_timer()
        self._silence_task = asyncio.create_task(self._silence_check())

    async def _silence_check(self) -> None:
        await asyncio.sleep(7.0)
        try:
            lang = self._default_language
            try:
                from sarvam_stt import _locked_language
                if _locked_language:
                    lang = _locked_language
            except Exception:
                pass
            phrase = _SILENCE_PHRASES.get(lang, _SILENCE_PHRASES["en-IN"])
            await self.session.say(phrase, add_to_chat_ctx=False)
        except Exception as e:
            logger.debug("Silence check failed: %s", e)

    def _cancel_filler_task(self) -> None:
        if self._filler_task and not self._filler_task.done():
            self._filler_task.cancel()
            self._filler_task = None

    async def _play_thinking_filler(self) -> None:
        global _filler_index
        try:
            phrase = _THINKING_FILLERS[_filler_index % len(_THINKING_FILLERS)]
            _filler_index += 1
            logger.info("Playing filler: %r", phrase)
            await self.session.say(phrase, add_to_chat_ctx=False)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("Filler error: %s", e)

    def on_agent_state_changed(self, ev) -> None:
        raw = getattr(ev, 'new_state', ev)
        state = str(raw).lower()
        logger.info("Agent state → %s", raw)
        if 'listen' in state:
            self._cancel_filler_task()
            self._start_silence_timer()
        elif 'think' in state:
            self._cancel_silence_timer()
        else:  # speaking
            self._cancel_filler_task()
            self._cancel_silence_timer()

    # ------------------------------------------------------------------

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:
        text = getattr(new_message, "text_content", None)
        if not text:
            return

        asyncio.create_task(_save_transcript(self._session_id, "user", text))
        self._cancel_silence_timer()

        try:
            trimmed = self.chat_ctx.copy().truncate(max_items=6)
            await self.update_chat_ctx(trimmed)
        except Exception as e:
            logger.warning("Context trim failed: %s", e)

        lower = text.lower()

        self._first_turn_done = True

        try:
            from sarvam_stt import _locked_language as _curr_locked
        except Exception:
            _curr_locked = ""

        if not _curr_locked:
            # Language not confirmed yet — detect on every turn until we get it
            detected = self._match_language(text)
            if detected:
                await self._do_language_switch(detected, turn_ctx)
        elif any(p in lower or p in text for p in _SWITCH_PHRASES):
            # Language already locked — only switch on explicit request
            new_lang = self._match_language(text)
            if new_lang:
                await self._do_language_switch(new_lang, turn_ctx)

        if not self._caller_name_saved:
            m = _USER_NAME_RE.search(text)
            if m:
                name = m.group(1).strip().title()
                self._caller_name_saved = True
                asyncio.create_task(_persist_caller_name(self._session_id, name))

    async def _do_language_switch(self, lang: str, turn_ctx) -> None:
        """Lock language first so TTS uses the right voice even if LLM starts responding
        during the filler synthesis, then play the switch filler."""
        self._set_language(lang)  # must come before any await
        # No filler or prompt change needed for English — it's already the default
        if lang == "en-IN":
            logger.info("Language switch to English — no filler, continuing")
            return
        logger.info("Language switch → %s, playing filler", lang)
        await self.session.say(_LANG_SWITCH_FILLER, add_to_chat_ctx=False)
        logger.info("Language locked: %s", lang)
        # Update agent instructions so LLM uses language-specific prompt from this turn on
        try:
            focused = build_locked_prompt(
                self._agent_name, self._org_name,
                self._org_description, self._instructions_str,
                lang,
            )
            await self.update_instructions(focused)
            logger.info("Instructions updated for %s (%d chars)", lang, len(focused))
        except Exception as e:
            logger.warning("update_instructions failed: %s", e)

    def _match_language(self, text: str) -> str | None:
        lower = text.lower()
        for token, code in _LANG_MAP.items():
            if token in lower or token in text:
                return code
        return None

    def _set_language(self, lang: str) -> None:
        try:
            import sarvam_stt
            sarvam_stt.lock_language(lang)
        except ImportError:
            pass

    def on_agent_reply(self, text: str) -> None:
        if not self._caller_name_saved and text:
            m = _AGENT_NAME_RE.search(text) or _AGENT_ECHO_NAME_RE.match(text)
            if m:
                name = m.group(1).strip().title()
                self._caller_name_saved = True
                asyncio.create_task(_persist_caller_name(self._session_id, name))


async def _save_transcript(session_id: str, speaker: str, message: str) -> None:
    try:
        await _api_client.post(
            f"{API_BASE_URL}/transcripts/",
            json={"session_id": session_id, "speaker": speaker, "message": message},
        )
    except Exception as e:
        logger.warning("Failed to save transcript: %s", e)


async def end_call(session_id, room_name=None, caller_id=None, start_time=None):
    try:
        await _api_client.post(f"{API_BASE_URL}/calls/",
            json={"session_id": session_id, "room_name": room_name,
                  "caller_id": caller_id, "start_time": start_time}, timeout=10.0)
        await _api_client.post(f"{API_BASE_URL}/calls/{session_id}/end", timeout=10.0)
        await _api_client.post(f"{API_BASE_URL}/calls/{session_id}/summarize", timeout=30.0)
        logger.info("Call ended and summarized: %s", session_id)
    except Exception as e:
        logger.error("Failed to end/summarize call %s: %s", session_id, e)
