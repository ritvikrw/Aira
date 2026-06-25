"""
Vector store with local multilingual embeddings + BM25 hybrid re-ranking.

Embedding model: paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers)
  - Runs locally in-process — zero network latency (~10-20ms vs ~200-300ms for OpenAI API)
  - 50+ languages including all Indian languages (Telugu, Hindi, Tamil, Kannada, Malayalam)
  - ~470MB model, downloaded once and cached in Docker image layer

Search: semantic retrieval (broad) → global BM25 augmentation → BM25 re-rank

NOTE: If you switch from OpenAI embeddings (text-embedding-3-small) to this model,
run POST /knowledge-base/reindex once to re-embed all existing documents.
"""

import asyncio
import os
import re
import threading
import logging
import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

COLLECTION_NAME = "knowledge_base_v4"   # new name — prevents collision with OpenAI-embedded data

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

_vector_store: Chroma | None = None
_embeddings: HuggingFaceEmbeddings | None = None
_embeddings_lock = threading.Lock()
_vector_store_lock = threading.Lock()

# BM25 state — rebuilt whenever documents are added/deleted
_bm25_corpus: list[str] = []
_bm25_index: BM25Okapi | None = None
_bm25_lock = threading.Lock()


def _tokenize(text: str) -> list[str]:
    """Regex tokenizer: splits on word boundaries, keeps hyphenated terms together."""
    return re.findall(r'\w+', text.lower())


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
        tokenized = [_tokenize(doc) for doc in docs]
        with _bm25_lock:
            _bm25_corpus = docs
            _bm25_index = BM25Okapi(tokenized) if tokenized else None
        logger.info("BM25 index rebuilt: %d chunks", len(docs))
    except Exception as e:
        logger.warning("BM25 rebuild failed: %s", e)


def _bm25_augment_candidates(query: str, sem_docs: list[Document], fetch_k: int) -> list[Document]:
    """Add top BM25 hits from the global index that weren't in the semantic results."""
    with _bm25_lock:
        bm25 = _bm25_index
        corpus = list(_bm25_corpus)
    if bm25 is None or not corpus:
        return sem_docs

    tokens = _tokenize(query)
    scores = bm25.get_scores(tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:fetch_k]

    seen = {d.page_content for d in sem_docs}
    extra: list[Document] = []
    for idx in top_indices:
        if scores[idx] > 0 and corpus[idx] not in seen:
            extra.append(Document(page_content=corpus[idx]))
            seen.add(corpus[idx])

    return sem_docs + extra


def _bm25_rerank(query: str, candidates: list[Document], top_k: int) -> list[Document]:
    """Re-rank candidates using BM25 keyword scoring to boost exact name matches."""
    if not candidates or len(candidates) <= 1:
        return candidates[:top_k]
    tokens = _tokenize(query)
    mini_bm25 = BM25Okapi([_tokenize(d.page_content) for d in candidates])
    scores = mini_bm25.get_scores(tokens)
    ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
    return [d for d, _ in ranked[:top_k]]


async def search(query: str, k: int = 4, language: str | None = None) -> list[str]:
    store = get_vector_store()
    where = {"language": language} if language else None
    fetch_k = min(k * 3, 15)

    # Wrap blocking ChromaDB call to avoid stalling the event loop
    docs = await asyncio.to_thread(store.similarity_search, query, k=fetch_k, filter=where)

    if not docs and language:
        docs = await asyncio.to_thread(store.similarity_search, query, k=fetch_k)

    if not docs:
        return []

    # Augment with global BM25 hits not caught by semantic search, then re-rank
    candidates = await asyncio.to_thread(_bm25_augment_candidates, query, docs, fetch_k)
    reranked = await asyncio.to_thread(_bm25_rerank, query, candidates, k)
    return [d.page_content for d in reranked]


async def search_with_scores(query: str, k: int = 4, language: str | None = None) -> list[tuple[str, float]]:
    store = get_vector_store()
    where = {"language": language} if language else None
    fetch_k = min(k * 3, 15)
    results = await asyncio.to_thread(
        store.similarity_search_with_relevance_scores, query, k=fetch_k, filter=where
    )
    if not results and language:
        results = await asyncio.to_thread(
            store.similarity_search_with_relevance_scores, query, k=fetch_k
        )
    if not results:
        return []

    docs = [r[0] for r in results]
    candidates = await asyncio.to_thread(_bm25_augment_candidates, query, docs, fetch_k)
    reranked = await asyncio.to_thread(_bm25_rerank, query, candidates, k)
    score_map = {r[0].page_content: r[1] for r in results}
    return [(d.page_content, score_map.get(d.page_content, 0.0)) for d in reranked]


async def add_documents(documents, doc_id: str) -> int:
    store = get_vector_store()
    for doc in documents:
        doc.metadata["doc_id"] = doc_id
    await asyncio.to_thread(store.add_documents, documents)
    await asyncio.to_thread(rebuild_bm25)
    return len(documents)


async def delete_document(doc_id: str):
    store = get_vector_store()
    await asyncio.to_thread(store.delete, where={"doc_id": doc_id})
    await asyncio.to_thread(rebuild_bm25)
