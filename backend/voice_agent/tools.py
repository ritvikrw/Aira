import asyncio
import logging
import os
import httpx
from livekit.agents import function_tool, RunContext  # function_tool used by search_knowledge_base

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
_api_client = httpx.AsyncClient(timeout=15.0)

# Max chars of KB text to inject per search — keeps it to ~150 tokens
# enough for the LLM to answer, not so much it bloats conversation history
_KB_MAX_CHARS = 600
_KB_FILLERS = ["Sure, let me check...", "One moment...", "Got it, checking...", "Let me look that up..."]
_kb_filler_index = 0


def _trim_kb(docs: list[str]) -> str:
    """Join KB chunks and trim to _KB_MAX_CHARS to limit tokens in history."""
    joined = "\n---\n".join(docs)
    if len(joined) > _KB_MAX_CHARS:
        return joined[:_KB_MAX_CHARS] + "…"
    return joined

# Sarvam language code → short tag used in ChromaDB
_LANG_TO_SHORT: dict[str, str] = {
    "te-IN": "te", "hi-IN": "hi", "ta-IN": "ta", "kn-IN": "kn",
    "ml-IN": "ml", "mr-IN": "mr", "bn-IN": "bn", "gu-IN": "gu",
    "pa-IN": "pa", "od-IN": "od", "en-IN": "en",
}


async def _persist_caller_name(session_id: str, name: str) -> None:
    """PATCH the call record with the caller's name. Called from agent.py — no tool overhead."""
    try:
        await _api_client.patch(
            f"{API_BASE_URL}/calls/{session_id}/caller",
            json={"caller_name": name},
        )
        logger.info("Caller name saved: %s (session=%s)", name, session_id)
    except Exception as e:
        logger.warning("Failed to save caller name: %s", e)


async def _kb_query(payload: dict) -> list[str]:
    """Single KB search request. Returns documents list or empty list on failure."""
    try:
        r = await _api_client.post(
            f"{API_BASE_URL}/knowledge-base/search",
            json=payload,
            timeout=15.0,
        )
        r.raise_for_status()
        return r.json().get("documents", [])
    except Exception:
        return []


@function_tool
async def search_knowledge_base(context: RunContext, query: str) -> str:  # noqa: C901
    """Search the company knowledge base to answer caller questions.

    Use this whenever the caller asks about company info, services, pricing,
    hours, FAQs, or anything factual about the organisation.

    Args:
        query: The caller's question or a search phrase derived from it.
    """
    # Play a rotating filler immediately — KB search takes ~1-2s and we need to cover the silence
    global _kb_filler_index
    try:
        session = getattr(context, "session", None)
        if session:
            phrase = _KB_FILLERS[_kb_filler_index % len(_KB_FILLERS)]
            _kb_filler_index += 1
            asyncio.create_task(session.say(phrase, add_to_chat_ctx=False))
    except Exception:
        pass

    try:
        from sarvam_stt import detected_language
        lang = _LANG_TO_SHORT.get(detected_language, "en")
    except Exception:
        lang = "en"

    try:
        # Fire language-specific and English queries in parallel to halve latency.
        # For English callers both queries are identical — deduplication is harmless.
        payloads: list[dict] = [{"query": query, "k": 2, "language": lang}]
        if lang != "en":
            payloads.append({"query": query, "k": 2, "language": "en"})

        results = await asyncio.gather(*[_kb_query(p) for p in payloads])

        # Return first non-empty result; fall back to unfiltered search if both empty
        for docs in results:
            if docs:
                return _trim_kb(docs)

        # Last resort: unfiltered search (no language filter)
        fallback = await _kb_query({"query": query, "k": 2})
        if fallback:
            return _trim_kb(fallback)

        return "No relevant information found. Tell the caller you'll get someone to follow up."

    except asyncio.CancelledError:
        logger.warning("KB search cancelled (user spoke during tool call)")
        return "Knowledge base unavailable. Tell the caller you'll get someone to call them back."
    except Exception as e:
        logger.error("KB search failed: %s", e)
        return "Knowledge base unavailable. Tell the caller you'll get someone to call them back."
