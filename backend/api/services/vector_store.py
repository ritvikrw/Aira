"""
Vector store with local multilingual embeddings + BM25 hybrid re-ranking.

Embedding model: paraphrase-multilingual-MiniLM-L12-v2
  - Runs locally, zero API calls → ~50 ms per query (vs 3-5 s with OpenAI)
  - Supports 50+ languages including Telugu, Hindi, Tamil
  - Telugu query → naturally matches English KB content about same topic

Search: semantic retrieval (broad) → BM25 re-rank (boosts exact name matches)
  - Catches both intent-based queries and exact product/brand name lookups
"""

import asyncio
import os
import threading
import logging
import chromadb
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "knowledge_base_v2"   # v2 = multilingual model; old v1 collection left untouched

_vector_store: Chroma | None = None
_embeddings: HuggingFaceEmbeddings | None = None
_embeddings_lock = threading.Lock()
_vector_store_lock = threading.Lock()

# BM25 state — rebuilt whenever documents are added/deleted
_bm25_corpus: list[str] = []
_bm25_index: BM25Okapi | None = None
_bm25_lock = threading.Lock()


def get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        with _embeddings_lock:
            if _embeddings is None:
                logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
                _embeddings = HuggingFaceEmbeddings(
                    model_name=EMBEDDING_MODEL,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
                logger.info("Embedding model loaded")
    return _embeddings


def get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        with _vector_store_lock:
            if _vector_store is None:
                persist_path = os.getenv("CHROMA_PERSIST_PATH", "./chroma_data")
                client = chromadb.PersistentClient(path=persist_path)
                _vector_store = Chroma(
                    client=client,
                    collection_name=COLLECTION_NAME,
                    embedding_function=get_embeddings(),
                )
    return _vector_store


def rebuild_bm25() -> None:
    """Rebuild the in-memory BM25 index from all stored chunks."""
    global _bm25_corpus, _bm25_index
    try:
        store = get_vector_store()
        result = store._collection.get(include=["documents"])
        docs = result.get("documents") or []
        tokenized = [doc.lower().split() for doc in docs]
        with _bm25_lock:
            _bm25_corpus = docs
            _bm25_index = BM25Okapi(tokenized) if tokenized else None
        logger.info("BM25 index rebuilt: %d chunks", len(docs))
    except Exception as e:
        logger.warning("BM25 rebuild failed: %s", e)


def _bm25_rerank(query: str, candidates: list, top_k: int) -> list:
    """Re-rank semantic search candidates using BM25 keyword scoring.
    Boosts exact product/brand name matches over pure semantic similarity."""
    if not candidates or len(candidates) <= 1:
        return candidates[:top_k]
    texts = [d.page_content for d in candidates]
    tokens = query.lower().split()
    mini_bm25 = BM25Okapi([t.lower().split() for t in texts])
    scores = mini_bm25.get_scores(tokens)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [d for d, _ in ranked[:top_k]]


async def search(query: str, k: int = 4, language: str | None = None) -> list[str]:
    store = get_vector_store()
    where = {"language": language} if language else None
    fetch_k = min(k * 3, 15)   # fetch broader set for re-ranking

    docs = store.similarity_search(query, k=fetch_k, filter=where)

    # Fallback 1: drop language filter
    if not docs and language:
        docs = store.similarity_search(query, k=fetch_k)

    if not docs:
        return []

    # BM25 re-rank: exact keyword matches bubble up
    reranked = await asyncio.to_thread(_bm25_rerank, query, docs, k)
    return [d.page_content for d in reranked]


async def search_with_scores(query: str, k: int = 4, language: str | None = None) -> list[tuple[str, float]]:
    store = get_vector_store()
    where = {"language": language} if language else None
    fetch_k = min(k * 3, 15)

    results = store.similarity_search_with_relevance_scores(query, k=fetch_k, filter=where)
    if not results and language:
        results = store.similarity_search_with_relevance_scores(query, k=fetch_k)
    if not results:
        return []

    docs = [r[0] for r in results]
    reranked = await asyncio.to_thread(_bm25_rerank, query, docs, k)
    score_map = {r[0].page_content: r[1] for r in results}
    return [(d.page_content, score_map.get(d.page_content, 0.0)) for d in reranked]


async def add_documents(documents, doc_id: str) -> int:
    store = get_vector_store()
    for doc in documents:
        doc.metadata["doc_id"] = doc_id
    store.add_documents(documents)
    rebuild_bm25()
    return len(documents)


async def delete_document(doc_id: str):
    store = get_vector_store()
    store.delete(where={"doc_id": doc_id})
    rebuild_bm25()
