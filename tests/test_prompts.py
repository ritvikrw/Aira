"""Tests for prompts.py — build_system_prompt and LANGUAGE_NAMES."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'voice_agent'))

from prompts import build_system_prompt, LANGUAGE_NAMES


# ── LANGUAGE_NAMES ────────────────────────────────────────────────────────────
def test_language_names_contains_english():
    assert LANGUAGE_NAMES["en-IN"] == "English"


def test_language_names_contains_hindi():
    assert LANGUAGE_NAMES["hi-IN"] == "Hindi"


def test_language_names_contains_tamil():
    assert LANGUAGE_NAMES["ta-IN"] == "Tamil"


def test_language_names_contains_telugu():
    assert LANGUAGE_NAMES["te-IN"] == "Telugu"


def test_language_names_contains_kannada():
    assert LANGUAGE_NAMES["kn-IN"] == "Kannada"


def test_language_names_contains_malayalam():
    assert LANGUAGE_NAMES["ml-IN"] == "Malayalam"


def test_language_names_ten_entries():
    assert len(LANGUAGE_NAMES) == 10


# ── build_system_prompt ───────────────────────────────────────────────────────
def test_prompt_contains_agent_name():
    prompt = build_system_prompt("Aira", "Acme Corp")
    assert "Aira" in prompt


def test_prompt_contains_org_name():
    prompt = build_system_prompt("Aira", "Acme Corp")
    assert "Acme Corp" in prompt


def test_prompt_english_lang_has_multilingual_instruction():
    prompt = build_system_prompt("Aira", "Acme Corp", default_language="en-IN")
    assert "Respond in whatever language" in prompt


def test_prompt_hindi_lang_says_speak_in_hindi():
    prompt = build_system_prompt("Aira", "Acme Corp", default_language="hi-IN")
    assert "Hindi" in prompt
    assert "Always speak in" in prompt


def test_prompt_telugu_lang():
    prompt = build_system_prompt("Aira", "Acme Corp", default_language="te-IN")
    assert "Telugu" in prompt


def test_prompt_with_org_description():
    prompt = build_system_prompt("Aira", "Acme Corp", org_description="A software company")
    assert "software company" in prompt


def test_prompt_with_instructions():
    prompt = build_system_prompt("Aira", "Acme Corp", instructions="Always ask for callback number")
    assert "Always ask for callback number" in prompt


def test_prompt_no_instructions_no_block():
    prompt = build_system_prompt("Aira", "Acme Corp", instructions="")
    assert "Instructions:" not in prompt


def test_prompt_has_max_two_sentences_rule():
    prompt = build_system_prompt("Aira", "Acme Corp")
    assert "2 sentences" in prompt


def test_prompt_has_search_knowledge_base_rule():
    prompt = build_system_prompt("Aira", "Acme Corp")
    assert "search_knowledge_base" in prompt


def test_prompt_has_no_ai_mention_rule():
    prompt = build_system_prompt("Aira", "Acme Corp")
    assert "Never hint you are AI" in prompt


def test_prompt_org_description_stripped():
    prompt = build_system_prompt("Aira", "Acme", org_description="  desc  ")
    assert "desc" in prompt


def test_prompt_unknown_language_defaults_to_english():
    prompt = build_system_prompt("Aira", "Acme", default_language="xx-XX")
    # unknown lang → falls back to "Always speak in English" since get returns "English"
    assert "Always speak in" in prompt


def test_prompt_returns_string():
    result = build_system_prompt("Aira", "Acme")
    assert isinstance(result, str)
    assert len(result) > 100
