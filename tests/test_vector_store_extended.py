"""Extended tests for vector_store.py — covering search and async functions."""
import sys
import os
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))


def _make_doc(text):
    d = MagicMock()
    d.page_content = text
    return d


def _mock_store(docs=None, scored_docs=None):
    store = MagicMock()
    store.similarity_search.return_value = docs or []
    store.similarity_search_with_relevance_scores.return_value = scored_docs or []
    store.add_documents = MagicMock()
    store.delete = MagicMock()
    store._collection = MagicMock()
    store._collection.get.return_value = {"documents": [d.page_content for d in (docs or [])]}
    return store


# ── get_embeddings ────────────────────────────────────────────────────────────
def test_get_embeddings_returns_cached():
    import vector_store
    mock_emb = MagicMock()
    with patch('vector_store.HuggingFaceEmbeddings', return_value=mock_emb):
        vector_store._embeddings = None
        e1 = vector_store.get_embeddings()
        e2 = vector_store.get_embeddings()
        assert e1 is e2
        vector_store._embeddings = None  # cleanup


# ── rebuild_bm25 ──────────────────────────────────────────────────────────────
def test_rebuild_bm25_with_docs():
    import vector_store
    mock_store = _mock_store(docs=[_make_doc("python programming"), _make_doc("java code")])
    with patch('vector_store.get_vector_store', return_value=mock_store):
        vector_store.rebuild_bm25()
        assert vector_store._bm25_corpus == ["python programming", "java code"]
        assert vector_store._bm25_index is not None


def test_rebuild_bm25_empty_store():
    import vector_store
    mock_store = _mock_store(docs=[])
    with patch('vector_store.get_vector_store', return_value=mock_store):
        vector_store.rebuild_bm25()
        assert vector_store._bm25_index is None


def test_rebuild_bm25_on_exception():
    import vector_store
    with patch('vector_store.get_vector_store', side_effect=Exception("store error")):
        # Should not raise
        vector_store.rebuild_bm25()


# ── search ────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_returns_results():
    import vector_store
    docs = [_make_doc("python tutorial"), _make_doc("python guide")]
    mock_store = _mock_store(docs=docs)
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search("python", k=2)
    assert len(result) == 2
    assert all(isinstance(r, str) for r in result)


@pytest.mark.asyncio
async def test_search_with_language_filter():
    import vector_store
    docs = [_make_doc("hello world")]
    mock_store = _mock_store(docs=docs)
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search("hello", k=1, language="en")
    assert len(result) == 1
    mock_store.similarity_search.assert_called_with("hello", k=3, filter={"language": "en"})


@pytest.mark.asyncio
async def test_search_fallback_on_language_empty():
    import vector_store
    no_lang_docs = [_make_doc("fallback content")]
    mock_store = MagicMock()
    mock_store.similarity_search.side_effect = [[], no_lang_docs]
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search("query", k=1, language="te")
    assert len(result) == 1
    assert result[0] == "fallback content"


@pytest.mark.asyncio
async def test_search_empty_returns_empty():
    import vector_store
    mock_store = _mock_store(docs=[])
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search("query", k=4)
    assert result == []


# ── search_with_scores ────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_search_with_scores_returns_tuples():
    import vector_store
    docs = [_make_doc("doc content")]
    mock_store = _mock_store(scored_docs=[(docs[0], 0.9)])
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search_with_scores("query", k=1)
    assert len(result) == 1
    assert result[0][0] == "doc content"
    assert result[0][1] == 0.9


@pytest.mark.asyncio
async def test_search_with_scores_language_fallback():
    import vector_store
    docs = [_make_doc("english content")]
    mock_store = MagicMock()
    mock_store.similarity_search_with_relevance_scores.side_effect = [[], [(docs[0], 0.8)]]
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search_with_scores("query", k=1, language="te")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_search_with_scores_empty_returns_empty():
    import vector_store
    mock_store = _mock_store(scored_docs=[])
    with patch('vector_store.get_vector_store', return_value=mock_store):
        result = await vector_store.search_with_scores("query")
    assert result == []


# ── add_documents ─────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_add_documents():
    import vector_store
    doc1 = _make_doc("test content")
    doc1.metadata = {}
    mock_store = _mock_store()
    with patch('vector_store.get_vector_store', return_value=mock_store), \
         patch('vector_store.rebuild_bm25'):
        count = await vector_store.add_documents([doc1], "doc-123")
    assert count == 1
    assert doc1.metadata["doc_id"] == "doc-123"
    mock_store.add_documents.assert_called_once()


# ── delete_document ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_document():
    import vector_store
    mock_store = _mock_store()
    with patch('vector_store.get_vector_store', return_value=mock_store), \
         patch('vector_store.rebuild_bm25') as mock_rebuild:
        await vector_store.delete_document("doc-456")
    mock_store.delete.assert_called_once_with(where={"doc_id": "doc-456"})
    mock_rebuild.assert_called_once()


# ── COLLECTION_NAME ───────────────────────────────────────────────────────────
def test_collection_name():
    import vector_store
    assert vector_store.COLLECTION_NAME == "knowledge_base_v2"


def test_embedding_model_name():
    import vector_store
    assert "multilingual" in vector_store.EMBEDDING_MODEL
