import logging
import os
import httpx
from livekit.agents import function_tool, RunContext  # function_tool used by search_knowledge_base

logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
_api_client = httpx.AsyncClient(timeout=5.0)

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


@function_tool
async def search_knowledge_base(context: RunContext, query: str) -> str:
    """Search the company knowledge base to answer caller questions.

    Use this whenever the caller asks about company info, services, pricing,
    hours, FAQs, or anything factual about the organisation.

    Args:
        query: The caller's question or a search phrase derived from it.
    """
    # Search in the caller's detected language first, fall back to English
    try:
        from sarvam_stt import detected_language
        lang = _LANG_TO_SHORT.get(detected_language, "en")
    except Exception:
        lang = "en"

    try:
        # Sequential fallback: language-specific → English → unfiltered.
        # Local embeddings are ~50 ms so sequential is fast and avoids wasteful parallel calls.
        payloads: list[dict] = [{"query": query, "k": 4, "language": lang}]
        if lang != "en":
            payloads.append({"query": query, "k": 4, "language": "en"})
        payloads.append({"query": query, "k": 4})

        for payload in payloads:
            try:
                r = await _api_client.post(
                    f"{API_BASE_URL}/knowledge-base/search",
                    json=payload,
                    timeout=5.0,
                )
                r.raise_for_status()
                docs = r.json().get("documents", [])
                if docs:
                    return "\n---\n".join(docs)
            except Exception:
                continue

        return "No relevant information found. Tell the caller you'll get someone to follow up."

    except asyncio.CancelledError:
        logger.warning("KB search cancelled (user spoke during tool call)")
        return "Knowledge base unavailable. Tell the caller you'll get someone to call them back."
    except Exception as e:
        logger.error("KB search failed: %s", e)
        return "Knowledge base unavailable. Tell the caller you'll get someone to call them back."
