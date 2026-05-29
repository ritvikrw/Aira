"""Direct tests for knowledge_base route handlers."""
import sys
import os
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

# Stubs are already set by conftest.py (services.summarizer) and test_knowledge_base.py (langchain)
# Just ensure services.ingestion and services.vector_store are available
if 'services.ingestion' not in sys.modules:
    sys.modules['services.ingestion'] = MagicMock(ingest_file=AsyncMock(return_value=5))

from routes.knowledge_base import (
    list_documents, delete_document_route, search_knowledge_base,
    save_text, translate_text, get_chunks_by_language, get_document_content,
    _detect_language_from_filename, _ai_organise,
    LANG_CODE_MAP, LANG_NAME_MAP,
)


def _mock_db():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.delete = AsyncMock()
    return db


def _make_exec_result(rows):
    r = MagicMock()
    r.scalars.return_value.all.return_value = rows
    r.scalar_one_or_none.return_value = None
    r.all.return_value = rows
    return r


# ── list_documents ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_documents_empty_direct():
    db = _mock_db()
    db.execute.return_value = _make_exec_result([])
    result = await list_documents(db)
    assert result == []


@pytest.mark.asyncio
async def test_list_documents_with_docs():
    db = _mock_db()
    doc = MagicMock()
    doc.id = "d1"
    doc.filename = "test.pdf"
    doc.file_type = "pdf"
    doc.chunk_count = 5
    doc.status = "ready"
    doc.created_at = None
    db.execute.return_value = _make_exec_result([doc])
    result = await list_documents(db)
    assert len(result) == 1
    assert result[0]["doc_id"] == "d1"
    assert result[0]["status"] == "ready"


# ── delete_document_route ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_document_not_found_direct():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await delete_document_route("no-doc", db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_success_direct():
    db = _mock_db()
    doc = MagicMock()
    db.get.return_value = doc
    with patch('routes.knowledge_base.delete_document', AsyncMock()):
        result = await delete_document_route("doc-1", db)
    assert result["deleted"] == "doc-1"
    db.delete.assert_called_once_with(doc)
    db.commit.assert_called_once()


# ── search_knowledge_base ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_empty_query():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await search_knowledge_base({"query": ""})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_search_returns_docs():
    with patch('routes.knowledge_base.search', AsyncMock(return_value=["doc1", "doc2"])):
        result = await search_knowledge_base({"query": "test", "k": 2})
    assert result["count"] == 2
    assert "doc1" in result["documents"]


@pytest.mark.asyncio
async def test_search_with_scores_flag():
    with patch('services.vector_store.search_with_scores',
               AsyncMock(return_value=[("doc1", 0.9)])):
        result = await search_knowledge_base({"query": "test", "include_scores": True})
    assert "documents" in result


@pytest.mark.asyncio
async def test_search_with_language():
    with patch('routes.knowledge_base.search', AsyncMock(return_value=["telugu doc"])) as mock_search:
        result = await search_knowledge_base({"query": "hello", "k": 3, "language": "te"})
    assert result["count"] == 1


# ── save_text ─────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_save_text_empty_content():
    from fastapi import HTTPException
    db = _mock_db()
    with pytest.raises(HTTPException) as exc:
        await save_text({"title": "Test", "content": ""}, db)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_save_text_success_direct(tmp_path):
    db = _mock_db()
    with patch('routes.knowledge_base.UPLOAD_DIR', tmp_path), \
         patch('asyncio.create_task'):
        result = await save_text({"title": "My Note", "content": "Some content"}, db)
    assert "doc_id" in result
    assert result["filename"] == "My Note.txt"
    assert result["status"] == "processing"
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_text_default_title(tmp_path):
    db = _mock_db()
    with patch('routes.knowledge_base.UPLOAD_DIR', tmp_path), \
         patch('asyncio.create_task'):
        result = await save_text({"content": "Content only"}, db)
    assert result["filename"] == "Note.txt"


# ── translate_text ────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_translate_text_empty():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await translate_text({"text": "", "target_language": "hi"})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_translate_text_success():
    mock_trans = MagicMock()
    mock_trans.return_value.translate.return_value = "नमस्ते"
    with patch('deep_translator.GoogleTranslator', mock_trans):
        result = await translate_text({"text": "Hello world", "target_language": "hi"})
    assert result["translated"] == "नमस्ते"
    assert result["target_language"] == "hi"


@pytest.mark.asyncio
async def test_translate_text_long_text(tmp_path):
    """Text over 4500 chars should be chunked."""
    mock_trans = MagicMock()
    mock_trans.return_value.translate.return_value = "translated"
    long_text = "Hello world. " * 400  # ~5200 chars
    with patch('deep_translator.GoogleTranslator', mock_trans):
        result = await translate_text({"text": long_text, "target_language": "hi"})
    assert "translated" in result["translated"]
    assert mock_trans.call_count >= 2  # Called at least twice for 2 chunks


@pytest.mark.asyncio
async def test_translate_text_error():
    from fastapi import HTTPException
    with patch('deep_translator.GoogleTranslator', side_effect=Exception("API error")):
        with pytest.raises(HTTPException) as exc:
            await translate_text({"text": "Hello", "target_language": "hi"})
    assert exc.value.status_code == 500


# ── get_chunks_by_language ────────────────────────────────────────────────────
def test_get_chunks_by_language():
    mock_store = MagicMock()
    mock_store._collection.get.return_value = {"documents": ["chunk1", "chunk2"]}

    async def _run():
        return await get_chunks_by_language(language="en")

    with patch('routes.knowledge_base.get_vector_store', return_value=mock_store):
        result = asyncio.run(_run())
    assert result["language"] == "en"
    assert result["count"] == 2


# ── get_document_content ──────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_document_content_not_found():
    from fastapi import HTTPException
    db = _mock_db()
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        await get_document_content("no-doc", db)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_document_content_success():
    db = _mock_db()
    doc = MagicMock()
    doc.filename = "test.pdf"
    db.get.return_value = doc
    mock_store = MagicMock()
    mock_store._collection.get.return_value = {"documents": ["chunk1", "chunk2"]}
    with patch('routes.knowledge_base.get_vector_store', return_value=mock_store):
        result = await get_document_content("doc-1", db)
    assert result["doc_id"] == "doc-1"
    assert result["chunk_count"] == 2
    assert "chunk1" in result["chunks"]


# ── _ai_organise ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_ai_organise_success():
    import json
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "## About Us\nThis is the organised content."
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(return_value=mock_resp)
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        result = await _ai_organise("raw messy text content", "https://example.com")
    assert "## About Us" in result


@pytest.mark.asyncio
async def test_ai_organise_fallback_on_error():
    mock_oai = MagicMock()
    mock_oai.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
    with patch('openai.AsyncOpenAI', return_value=mock_oai):
        result = await _ai_organise("raw text", "https://example.com")
    assert result == "raw text"


# ── LANG_CODE_MAP / LANG_NAME_MAP ────────────────────────────────────────────
def test_lang_code_map_size():
    assert len(LANG_CODE_MAP) >= 10


def test_lang_name_map_size():
    assert len(LANG_NAME_MAP) >= 10
