"""Tests for voice_agent/agent.py."""
import sys
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# conftest.py stubs livekit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))

# Stub Agent base class before import
import agent as agent_module


# ── _GREETINGS ────────────────────────────────────────────────────────────────
def test_greetings_has_all_languages():
    from agent import _GREETINGS
    assert "en-IN" in _GREETINGS
    assert "hi-IN" in _GREETINGS
    assert "te-IN" in _GREETINGS
    assert "ta-IN" in _GREETINGS


def test_greetings_format_has_placeholders():
    from agent import _GREETINGS
    for lang, template in _GREETINGS.items():
        assert "{org}" in template
        assert "{name}" in template


# ── _USER_NAME_RE ─────────────────────────────────────────────────────────────
def test_user_name_re_matches_my_name_is():
    from agent import _USER_NAME_RE
    m = _USER_NAME_RE.search("Hi, my name is John Doe")
    assert m is not None
    assert m.group(1) == "John Doe"


def test_user_name_re_matches_my_names():
    from agent import _USER_NAME_RE
    m = _USER_NAME_RE.search("my name's Alice")
    assert m is not None
    assert "Alice" in m.group(1)


def test_user_name_re_no_match():
    from agent import _USER_NAME_RE
    m = _USER_NAME_RE.search("I want to talk about billing")
    assert m is None


# ── _AGENT_NAME_RE ────────────────────────────────────────────────────────────
def test_agent_name_re_matches_thank_you():
    from agent import _AGENT_NAME_RE
    m = _AGENT_NAME_RE.search("thank you, John!")
    assert m is not None
    assert "John" in m.group(1)


def test_agent_name_re_matches_got_it():
    from agent import _AGENT_NAME_RE
    m = _AGENT_NAME_RE.search("got it, Jane.")
    assert m is not None


def test_agent_name_re_no_match():
    from agent import _AGENT_NAME_RE
    m = _AGENT_NAME_RE.search("I'll transfer your call now")
    assert m is None


# ── ReceptionistAgent ─────────────────────────────────────────────────────────
def test_receptionist_agent_init():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(
        session_id="test-sess",
        agent_name="Aira",
        org_name="Acme Corp",
        default_language="en-IN",
    )
    assert a._session_id == "test-sess"
    assert a._agent_name == "Aira"
    assert a._org_name == "Acme Corp"
    assert a._caller_name_saved is False


@pytest.mark.asyncio
async def test_on_enter_english():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(
        session_id="s1", agent_name="Aira", org_name="Acme", default_language="en-IN"
    )
    a.session = AsyncMock()
    a.session.say = AsyncMock()
    await a.on_enter()
    a.session.say.assert_called_once()
    greeting = a.session.say.call_args[0][0]
    assert "Acme" in greeting


@pytest.mark.asyncio
async def test_on_enter_hindi():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(
        session_id="s2", agent_name="Aira", org_name="Acme", default_language="hi-IN"
    )
    a.session = AsyncMock()
    a.session.say = AsyncMock()
    await a.on_enter()
    a.session.say.assert_called_once()
    greeting = a.session.say.call_args[0][0]
    assert "Acme" in greeting


@pytest.mark.asyncio
async def test_on_user_turn_completed_saves_transcript():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s3", agent_name="Aira", org_name="Acme")
    msg = MagicMock()
    msg.text_content = "Hello I need help"
    with patch('agent._save_transcript', AsyncMock()) as mock_save, \
         patch('asyncio.create_task') as mock_task:
        await a.on_user_turn_completed(MagicMock(), msg)
        mock_task.assert_called()


@pytest.mark.asyncio
async def test_on_user_turn_completed_detects_name():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s4", agent_name="Aira", org_name="Acme")
    msg = MagicMock()
    msg.text_content = "Hi, my name is John Smith"
    with patch('asyncio.create_task') as mock_task:
        await a.on_user_turn_completed(MagicMock(), msg)
    assert a._caller_name_saved is True
    assert mock_task.call_count == 2  # save_transcript + persist_caller_name


@pytest.mark.asyncio
async def test_on_user_turn_completed_no_name():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s5", agent_name="Aira", org_name="Acme")
    msg = MagicMock()
    msg.text_content = "What are your services?"
    with patch('asyncio.create_task'):
        await a.on_user_turn_completed(MagicMock(), msg)
    assert a._caller_name_saved is False


def test_on_agent_reply_detects_name():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s6", agent_name="Aira", org_name="Acme")
    with patch('asyncio.create_task') as mock_task:
        a.on_agent_reply("thank you, Alice!")
    assert a._caller_name_saved is True
    mock_task.assert_called_once()


def test_on_agent_reply_no_name():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s7", agent_name="Aira", org_name="Acme")
    a.on_agent_reply("Sure, let me check that for you.")
    assert a._caller_name_saved is False


def test_on_agent_reply_already_saved():
    from agent import ReceptionistAgent
    a = ReceptionistAgent(session_id="s8", agent_name="Aira", org_name="Acme")
    a._caller_name_saved = True
    with patch('asyncio.create_task') as mock_task:
        a.on_agent_reply("thank you, Bob!")
    mock_task.assert_not_called()


# ── _save_transcript ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_transcript_success():
    from agent import _save_transcript
    mock_resp = MagicMock()
    agent_module._api_client.post = AsyncMock(return_value=mock_resp)
    await _save_transcript("sess-1", "user", "Hello")
    agent_module._api_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_save_transcript_failure_silent():
    from agent import _save_transcript
    agent_module._api_client.post = AsyncMock(side_effect=Exception("Network error"))
    await _save_transcript("sess-2", "user", "Hello")  # Should not raise


# ── end_call ──────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_end_call_success():
    from agent import end_call
    mock_resp = MagicMock()
    agent_module._api_client.post = AsyncMock(return_value=mock_resp)
    await end_call("sess-end-1", room_name="room-1", caller_id="c-1")
    assert agent_module._api_client.post.call_count == 3


@pytest.mark.asyncio
async def test_end_call_failure_silent():
    from agent import end_call
    agent_module._api_client.post = AsyncMock(side_effect=Exception("Network error"))
    await end_call("sess-end-2")  # Should not raise
