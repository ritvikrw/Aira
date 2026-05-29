"""Tests for services/summarizer.py — mocking LangChain."""
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api', 'services'))


def _import_summarizer():
    """Import summarizer with langchain stubbed out."""
    lc_openai = MagicMock()
    lc_openai.ChatOpenAI = MagicMock(return_value=MagicMock())

    lc_prompts = MagicMock()
    mock_prompt_obj = MagicMock()
    mock_prompt_obj.__or__ = MagicMock(return_value=MagicMock())
    lc_prompts.ChatPromptTemplate.from_messages = MagicMock(return_value=mock_prompt_obj)

    lc_parsers = MagicMock()

    with patch.dict('sys.modules', {
        'langchain_openai': lc_openai,
        'langchain_core': MagicMock(),
        'langchain_core.prompts': lc_prompts,
        'langchain_core.output_parsers': lc_parsers,
    }):
        if 'summarizer' in sys.modules:
            del sys.modules['summarizer']
        import summarizer
    return summarizer


@pytest.mark.asyncio
async def test_summarize_empty_transcripts():
    summarizer = _import_summarizer()
    result = await summarizer.summarize_call([])
    assert result["call_category"] == "Other"
    assert result["summary_text"] == "No transcript available."
    assert result["key_topics"] == []


@pytest.mark.asyncio
async def test_summarize_with_transcripts():
    summarizer = _import_summarizer()
    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(return_value={
        "summary_text": "Customer asked about pricing",
        "call_category": "Product Enquiry",
        "key_topics": ["pricing", "demo"],
        "action_items": ["Send pricing sheet"],
    })
    summarizer._chain = mock_chain

    result = await summarizer.summarize_call([
        {"speaker": "user", "message": "What is your pricing?"},
        {"speaker": "agent", "message": "I can help with that."},
    ])
    assert result["call_category"] == "Product Enquiry"
    assert "pricing" in result["key_topics"]


@pytest.mark.asyncio
async def test_summarize_invalid_category_falls_back():
    summarizer = _import_summarizer()
    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(return_value={
        "summary_text": "Test summary",
        "call_category": "InvalidCategory",
        "key_topics": [],
        "action_items": [],
    })
    summarizer._chain = mock_chain

    result = await summarizer.summarize_call([
        {"speaker": "user", "message": "Hello"}
    ])
    assert result["call_category"] == "Other"


@pytest.mark.asyncio
async def test_summarize_llm_failure_returns_fallback():
    summarizer = _import_summarizer()
    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(side_effect=Exception("LLM unavailable"))
    summarizer._chain = mock_chain

    result = await summarizer.summarize_call([
        {"speaker": "user", "message": "I have a complaint"}
    ])
    assert result["summary_text"] == "Summarization failed."
    assert result["call_category"] == "Other"


def test_categories_list():
    summarizer = _import_summarizer()
    assert "Product Enquiry" in summarizer.CATEGORIES
    assert "Support Request" in summarizer.CATEGORIES
    assert "Billing & Pricing" in summarizer.CATEGORIES
    assert "Other" in summarizer.CATEGORIES
    assert len(summarizer.CATEGORIES) == 7


@pytest.mark.asyncio
async def test_summarize_agent_and_user_messages():
    summarizer = _import_summarizer()
    mock_chain = AsyncMock()
    mock_chain.ainvoke = AsyncMock(return_value={
        "summary_text": "Test",
        "call_category": "Support Request",
        "key_topics": ["issue"],
        "action_items": [],
    })
    summarizer._chain = mock_chain

    transcripts = [
        {"speaker": "agent", "message": "Hello, how can I help?"},
        {"speaker": "user", "message": "I have an issue"},
        {"speaker": "agent", "message": "I'll escalate this"},
    ]
    result = await summarizer.summarize_call(transcripts)
    assert result["call_category"] == "Support Request"
    call_args = mock_chain.ainvoke.call_args
    assert "transcript" in call_args[0][0]
    assert "AGENT" in call_args[0][0]["transcript"]
    assert "USER" in call_args[0][0]["transcript"]
