"""
Tests for vector_store utility functions.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api', 'services'))


def make_doc(content):
    """Create a simple mock document with page_content."""
    doc = MagicMock()
    doc.page_content = content
    return doc


def test_bm25_rerank_empty():
    """_bm25_rerank with empty candidates returns empty."""
    from vector_store import _bm25_rerank
    result = _bm25_rerank("query", [], top_k=5)
    assert result == []


def test_bm25_rerank_single():
    """_bm25_rerank with single candidate returns it."""
    from vector_store import _bm25_rerank
    doc = make_doc("single document content")
    result = _bm25_rerank("query", [doc], top_k=5)
    assert len(result) == 1
    assert result[0].page_content == "single document content"


def test_bm25_rerank_ranks_higher_matching_first():
    """_bm25_rerank returns the expected number of results with multiple docs."""
    from vector_store import _bm25_rerank
    doc1 = make_doc("completely unrelated content about weather")
    doc2 = make_doc("python programming language features")
    doc3 = make_doc("python python python code development")
    result = _bm25_rerank("python", [doc1, doc2, doc3], top_k=2)
    # result should contain only docs with 'python', not the unrelated one
    result_texts = [r.page_content for r in result]
    assert len(result) == 2
    # The unrelated doc should not be the top result
    assert result[0].page_content != doc1.page_content


def test_bm25_rerank_top_k_limits_results():
    """_bm25_rerank respects top_k limit."""
    from vector_store import _bm25_rerank
    docs = [make_doc(f"document number {i}") for i in range(10)]
    result = _bm25_rerank("document", docs, top_k=3)
    assert len(result) == 3


def test_get_vector_store_double_checked_locking():
    """get_vector_store double-checked locking doesn't break under multiple calls."""
    import vector_store

    mock_store = MagicMock()

    with patch('vector_store.chromadb.PersistentClient') as mock_client, \
         patch('vector_store.get_embeddings') as mock_emb, \
         patch('vector_store.Chroma') as mock_chroma:
        mock_chroma.return_value = mock_store
        # Reset global state
        vector_store._vector_store = None

        store1 = vector_store.get_vector_store()
        # Second call should return same instance (cached)
        store2 = vector_store.get_vector_store()
        assert store1 is store2

        # Reset for other tests
        vector_store._vector_store = None
