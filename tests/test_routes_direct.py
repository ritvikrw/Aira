"""
Tests that call route handler functions directly (not via TestClient) to ensure
async function bodies are traced by coverage.
"""
import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

# Import route handlers directly
from routes.calls import (
    start_call, end_call, list_calls, get_call, update_caller_info,
    delete_all_calls, cleanup_stale_calls_endpoint, get_analytics,
    recategorize_calls, summarize, CallStartIn, CallerInfoIn,
)
from routes.transcripts import create_transcript, get_transcripts, TranscriptIn
from routes.settings import get_settings, update_settings, list_voices, list_languages
from routes.internal import save_metrics, list_metrics, metrics_summary, MetricsIn
from routes.translate import translate_texts, TranslateRequest


# ── Helpers ───────────────────────────────────────────────────────────────────
def _mock_db():
    """Create a mock AsyncSession."""
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    db.refresh = AsyncMock()
    db.scalar = AsyncMock(return_value=0)
    return db


def _make_result(rows):
    """Make a mock execute result."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    result.scalar_one_or_none.return_value = None
    result.all.return_value = rows
    result.fetchall.return_value = []
    return result


# ── calls.start_call ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_start_call_new():
    db = _mock_db()
    db.get.return_value = None
    result = await start_call(CallStartIn(session_id="direct-1"), db)
    assert result["session_id"] == "direct-1"
    assert result["status"] == "active"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_start_call_existing():
    db = _mock_db()
    existing = MagicMock()
    existing.session_id = "direct-exist"
    existing.status = "active"
    db.get.return_value = existing
    result = await start_call(CallStartIn(session_id="direct-exist"), db)
    assert result["session_id"] == "direct-exist"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_start_call_with_valid_start_time():
    db = _mock_db()
    db.get.return_value = None
    result = await start_call(
        CallStartIn(session_id="direct-time", start_time="2024-01-15T10:00:00"), db
    )
    assert result["status"] == "active"


@pytest.mark.asyncio
async def test_start_call_with_invalid_start_time():
    db = _mock_db()
    db.get.return_value = None
    result = await start_call(
        CallStartIn(session_id="direct-bad-time", start_time="not-a-date"), db
    )
    assert result["status"] == "active"


# ── calls.end_call ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_end_call_new_session():
    db = _mock_db()
    db.get.return_value = None
    result = await end_call("new-end-sess", db)
    assert result["session_id"] == "new-end-sess"
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_end_call_existing_no_start_time():
    db = _mock_db()
    existing = MagicMock()
    existing.call_start_time = None
    existing.call_duration_seconds = None
    db.get.return_value = existing
    result = await end_call("end-no-start", db)
    assert result["session_id"] == "end-no-start"
    assert existing.status == "ended"


# ── calls.update_caller_info ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_update_caller_info_success():
    db = _mock_db()
    existing = MagicMock()
    existing.caller_name = None
    db.get.return_value = existing
    result = await update_caller_info("sess-patch", CallerInfoIn(caller_name="John"), db)
    assert result["caller_name"] == "John"
    assert existing.caller_name == "John"


@pytest.mark.asyncio
async def test_update_caller_info_not_found():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await update_caller_info("no-sess", CallerInfoIn(caller_name="X"), db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_caller_info_empty_name_sets_none():
    db = _mock_db()
    existing = MagicMock()
    existing.caller_name = "Old Name"
    db.get.return_value = existing
    result = await update_caller_info("sess-null", CallerInfoIn(caller_name=""), db)
    assert result["caller_name"] is None


# ── calls.get_call ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_call_not_found():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await get_call("no-call", db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_call_without_summary():
    db = _mock_db()
    log = MagicMock()
    log.session_id = "g1"
    log.caller_id = None
    log.caller_name = None
    log.caller_phone = None
    log.room_name = None
    log.status = "active"
    log.call_start_time = None
    log.call_end_time = None
    log.call_duration_seconds = None
    db.get.return_value = log
    db.execute.return_value = _make_result([])
    db.execute.return_value.scalar_one_or_none.return_value = None
    result = await get_call("g1", db)
    assert result["session_id"] == "g1"
    assert result["summary"] is None


@pytest.mark.asyncio
async def test_get_call_with_summary():
    db = _mock_db()
    log = MagicMock()
    log.session_id = "g2"
    log.caller_id = None
    log.caller_name = None
    log.caller_phone = None
    log.room_name = None
    log.status = "ended"
    log.call_start_time = None
    log.call_end_time = None
    log.call_duration_seconds = None
    db.get.return_value = log
    summary = MagicMock()
    summary.summary_text = "Test"
    summary.key_topics = ["t1"]
    summary.action_items = []
    summary.call_category = "Other"
    db.execute.return_value = _make_result([])
    db.execute.return_value.scalar_one_or_none.return_value = summary
    result = await get_call("g2", db)
    assert result["summary"]["summary_text"] == "Test"


# ── calls.delete_all_calls ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_all_calls_direct():
    db = _mock_db()
    db.execute = AsyncMock()
    result = await delete_all_calls(db)
    assert result["deleted"] is True
    assert db.commit.called


# ── calls.cleanup_stale ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cleanup_stale_direct():
    db = _mock_db()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("sess-old",), ("sess-old2",)]
    db.execute.return_value = mock_result
    result = await cleanup_stale_calls_endpoint(threshold_minutes=60, db=db)
    assert result["fixed"] == 2
    assert "sess-old" in result["session_ids"]


# ── calls.recategorize ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_recategorize_calls_direct():
    db = _mock_db()
    # No sessions with transcripts
    no_result = MagicMock()
    no_result.all.return_value = []
    db.execute.return_value = no_result
    result = await recategorize_calls(db)
    assert result["processed"] == 0
    assert result["total_needing_update"] == 0


# ── calls.list_calls ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_calls_direct():
    db = _mock_db()
    mock_row = MagicMock()
    mock_row.CallLog.session_id = "list-1"
    mock_row.CallLog.caller_id = None
    mock_row.CallLog.caller_name = None
    mock_row.CallLog.caller_phone = None
    mock_row.CallLog.status = "active"
    mock_row.CallLog.call_start_time = None
    mock_row.CallLog.call_duration_seconds = None
    mock_row.CallLog.room_name = None
    mock_row.call_category = "Other"
    mock_row.summary_text = "Test"
    mock_row.key_topics = ["t1"]
    mock_row.action_items = []
    db.execute.return_value = MagicMock()
    db.execute.return_value.all.return_value = [mock_row]
    result = await list_calls(db=db)
    assert len(result) == 1
    assert result[0]["session_id"] == "list-1"


# ── calls.summarize ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_summarize_not_found():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await summarize("no-sess", db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_summarize_no_transcripts():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = MagicMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    with pytest.raises(HTTPException) as exc:
        await summarize("no-tx-sess", db)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_summarize_creates_new_summary():
    db = _mock_db()
    db.get.return_value = MagicMock()
    # Transcripts exist
    tx = MagicMock()
    tx.speaker = "user"
    tx.message = "Hello"
    tx_result = MagicMock()
    tx_result.scalars.return_value.all.return_value = [tx]
    # No existing summary
    sum_result = MagicMock()
    sum_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [tx_result, sum_result]
    result = await summarize("sum-sess", db)
    assert "summary_text" in result
    db.add.assert_called_once()


# ── calls.get_analytics ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_analytics_direct():
    db = _mock_db()
    db.scalar = AsyncMock(return_value=0)
    daily_result = MagicMock()
    daily_result.all.return_value = []
    hour_result = MagicMock()
    hour_result.scalars.return_value.all.return_value = []
    cat_result = MagicMock()
    cat_result.all.return_value = []
    topics_result = MagicMock()
    topics_result.all.return_value = []
    db.execute.side_effect = [daily_result, hour_result, cat_result, topics_result]
    result = await get_analytics(db=db)
    assert "total_calls" in result
    assert "categories" in result


@pytest.mark.asyncio
async def test_analytics_with_dates_direct():
    db = _mock_db()
    db.scalar = AsyncMock(return_value=5)
    daily_result = MagicMock()
    daily_result.all.return_value = []
    hour_result = MagicMock()
    hour_result.scalars.return_value.all.return_value = []
    cat_result = MagicMock()
    cat_result.all.return_value = [("Billing & Pricing",)]
    topics_result = MagicMock()
    topics_result.all.return_value = [(['billing', 'refund'],)]
    db.execute.side_effect = [daily_result, hour_result, cat_result, topics_result]
    result = await get_analytics(
        start_date="2024-01-01", end_date="2024-12-31",
        tz="Asia/Kolkata", db=db
    )
    assert result["total_calls"] == 5
    assert len(result["categories"]) == 1


# ── transcripts ───────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_transcript_direct():
    db = _mock_db()
    row = MagicMock()
    row.id = 1
    row.session_id = "tx-direct-1"
    row.speaker = "user"
    db.refresh = AsyncMock(side_effect=lambda r: None)
    with patch('routes.transcripts.Transcript', return_value=row):
        result = await create_transcript(
            TranscriptIn(session_id="tx-direct-1", speaker="user", message="Hi"), db
        )
    assert result["speaker"] == "user"


@pytest.mark.asyncio
async def test_create_transcript_invalid_speaker_direct():
    from fastapi import HTTPException
    db = _mock_db()
    with pytest.raises(HTTPException) as exc:
        await create_transcript(
            TranscriptIn(session_id="tx-bad", speaker="robot", message="Beep"), db
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_transcripts_direct():
    db = _mock_db()
    tx = MagicMock()
    tx.id = 1
    tx.speaker = "user"
    tx.message = "Hello"
    tx.created_at = None
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [tx]
    db.execute.return_value = result_mock
    result = await get_transcripts("sess-1", db)
    assert len(result) == 1
    assert result[0]["speaker"] == "user"


# ── settings ──────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_settings_direct():
    db = _mock_db()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    result = await get_settings(db)
    assert "selected_voice_id" in result
    assert result["default_language"] == "en-IN"


@pytest.mark.asyncio
async def test_get_settings_with_stored_values():
    db = _mock_db()
    setting = MagicMock()
    setting.key = "selected_voice_id"
    setting.value = "nova"
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [setting]
    db.execute.return_value = result_mock
    result = await get_settings(db)
    assert result["selected_voice_id"] == "nova"


@pytest.mark.asyncio
async def test_update_settings_direct():
    db = _mock_db()
    db.get.return_value = None
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    result = await update_settings({"selected_voice_id": "alloy"}, db)
    assert "selected_voice_id" in result
    db.add.assert_called()


@pytest.mark.asyncio
async def test_update_settings_overwrite():
    db = _mock_db()
    existing = MagicMock()
    existing.value = "old_value"
    db.get.return_value = existing
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    await update_settings({"agent_name": "NewBot"}, db)
    assert existing.value == "NewBot"


def test_list_voices_direct():
    result = list_voices()
    assert len(result) > 0
    assert all("voice_id" in v for v in result)


def test_list_languages_direct():
    result = list_languages()
    assert len(result) > 0
    codes = [l["code"] for l in result]
    assert "en-IN" in codes


# ── internal.metrics ──────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_metrics_new_direct():
    db = _mock_db()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    db.execute.return_value = result_mock
    result = await save_metrics("m-direct-1", MetricsIn(llm_prompt_tokens=10), db)
    assert result["ok"] is True
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_save_metrics_accumulate_direct():
    db = _mock_db()
    existing = MagicMock()
    existing.llm_prompt_tokens = 100
    existing.llm_completion_tokens = 50
    existing.llm_requests = 1
    existing.tts_characters = 200
    existing.tts_requests = 1
    existing.stt_requests = 1
    existing.stt_audio_duration_ms = 1000.0
    existing.llm_ttft_ms = None
    existing.tts_ttfb_ms = None
    existing.stt_ttft_ms = None
    existing.tts_provider = None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing
    db.execute.return_value = result_mock
    result = await save_metrics("m-acc", MetricsIn(
        llm_prompt_tokens=50, llm_ttft_ms=100.0, tts_provider="Sarvam"
    ), db)
    assert result["ok"] is True
    assert existing.llm_ttft_ms == 100.0
    assert existing.tts_provider == "Sarvam"


@pytest.mark.asyncio
async def test_list_metrics_direct():
    db = _mock_db()
    m = MagicMock()
    m.CallMetrics.session_id = "m1"
    m.CallMetrics.llm_prompt_tokens = 10
    m.CallMetrics.llm_completion_tokens = 5
    m.CallMetrics.llm_ttft_ms = None
    m.CallMetrics.llm_requests = 1
    m.CallMetrics.tts_provider = None
    m.CallMetrics.tts_characters = 100
    m.CallMetrics.tts_ttfb_ms = None
    m.CallMetrics.tts_requests = 1
    m.CallMetrics.stt_audio_duration_ms = None
    m.CallMetrics.stt_ttft_ms = None
    m.CallMetrics.stt_requests = 1
    m.caller_name = None
    m.caller_id = None
    m.call_start_time = None
    m.call_duration_seconds = None
    m.status = "ended"
    result_mock = MagicMock()
    result_mock.all.return_value = [m]
    db.execute.return_value = result_mock
    result = await list_metrics(db)
    assert len(result) == 1
    assert result[0]["session_id"] == "m1"
    assert result[0]["llm_total_tokens"] == 15


@pytest.mark.asyncio
async def test_metrics_summary_empty_direct():
    db = _mock_db()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    db.execute.return_value = result_mock
    result = await metrics_summary(db)
    assert result["total_calls"] == 0
    assert result["avg_llm_ttft_ms"] is None


@pytest.mark.asyncio
async def test_metrics_summary_with_data_direct():
    db = _mock_db()
    m = MagicMock()
    m.llm_ttft_ms = 200.0
    m.tts_ttfb_ms = 100.0
    m.stt_ttft_ms = 50.0
    m.llm_prompt_tokens = 100
    m.llm_completion_tokens = 50
    m.tts_characters = 500
    m.stt_audio_duration_ms = 2000.0
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [m]
    db.execute.return_value = result_mock
    result = await metrics_summary(db)
    assert result["total_calls"] == 1
    assert result["avg_llm_ttft_ms"] == 200.0
    assert result["total_tts_characters"] == 500


# ── translate ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_translate_empty_direct():
    result = await translate_texts(TranslateRequest(texts=[]))
    assert result["translations"] == []


@pytest.mark.asyncio
async def test_translate_all_empty_strings_direct():
    result = await translate_texts(TranslateRequest(texts=["", " "]))
    assert result["translations"] == ["", " "]


@pytest.mark.asyncio
async def test_translate_success_direct():
    from unittest.mock import AsyncMock, MagicMock
    import json
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps({"translations": ["Hello"]})
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(return_value=mock_resp)
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        result = await translate_texts(TranslateRequest(texts=["नमस्ते"]))
    assert result["translations"] == ["Hello"]


@pytest.mark.asyncio
async def test_translate_failure_fallback_direct():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(side_effect=Exception("down"))
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        result = await translate_texts(TranslateRequest(texts=["नमस्ते"]))
    assert result["translations"] == ["नमस्ते"]
