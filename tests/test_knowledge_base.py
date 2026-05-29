"""Tests for knowledge_base.py — pure functions and routes with mocked services."""
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))

# Stub heavy dependencies BEFORE any import of routes.knowledge_base or services.ingestion
_lc_community_mock = MagicMock()
_lc_community_mock.document_loaders = MagicMock()
sys.modules.setdefault('langchain_community', _lc_community_mock)
sys.modules.setdefault('langchain_community.document_loaders', _lc_community_mock.document_loaders)
sys.modules.setdefault('services.ingestion', MagicMock(ingest_file=AsyncMock(return_value=5)))
sys.modules.setdefault('deep_translator', MagicMock())
# Only stub bs4/lxml if they're not already installed (avoid breaking importlib.util.find_spec)
try:
    import bs4  # noqa: F401
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False
    import importlib.util
    _bs4_mock = MagicMock()
    _bs4_mock.__spec__ = importlib.util.ModuleSpec('bs4', None)
    sys.modules.setdefault('bs4', _bs4_mock)
try:
    import lxml  # noqa: F401
except ImportError:
    _lxml_mock = MagicMock()
    _lxml_mock.__spec__ = importlib.util.ModuleSpec('lxml', None)
    sys.modules.setdefault('lxml', _lxml_mock)
    sys.modules.setdefault('lxml.etree', MagicMock())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import String, Integer, Text, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class KBBase(DeclarativeBase):
    pass


class KnowledgeDocumentTest(KBBase):
    __tablename__ = "knowledge_documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filename: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(16))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="processing")
    error_msg: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP)


@pytest.fixture(scope="module")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(KBBase.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(KBBase.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


def _make_kb_client(db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    mock_vs = MagicMock()
    mock_vs.search = AsyncMock(return_value=[])
    mock_vs.search_with_scores = AsyncMock(return_value=[])
    mock_vs.delete_document = AsyncMock()
    mock_vs.get_vector_store = MagicMock(return_value=mock_vs)

    with patch.dict('sys.modules', {
        'services.vector_store': mock_vs,
        'services.ingestion': MagicMock(ingest_file=AsyncMock(return_value=5)),
        'langchain_community': MagicMock(),
        'langchain_community.document_loaders': MagicMock(),
        'deep_translator': MagicMock(),
        'bs4': MagicMock(),
    }):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            if 'routes.knowledge_base' in sys.modules:
                del sys.modules['routes.knowledge_base']

            from database import get_db
            from routes.knowledge_base import router

            app = FastAPI()
            app.include_router(router)

            async def override():
                yield db_session

            app.dependency_overrides[get_db] = override
            return TestClient(app, raise_server_exceptions=True), mock_vs


@pytest.fixture
def kb_client(db_session):
    client, mock_vs = _make_kb_client(db_session)
    with client as c:
        yield c, mock_vs


# ── Pure functions ────────────────────────────────────────────────────────────
def test_detect_language_from_filename_english():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("doc.pdf") == "en"


def test_detect_language_from_filename_tamil():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("document [Tamil].pdf") == "ta"


def test_detect_language_from_filename_hindi():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("faq [Hindi].pdf") == "hi"


def test_detect_language_from_filename_telugu():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("guide [Telugu].pdf") == "te"


def test_detect_language_from_filename_unknown_lang():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("doc [Unknown].pdf") == "en"


def test_detect_language_from_filename_no_bracket():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("nodocument.pdf") == "en"


def test_detect_language_french():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("doc [French].txt") == "fr"


def test_detect_language_german():
    from routes.knowledge_base import _detect_language_from_filename
    assert _detect_language_from_filename("doc [German].txt") == "de"


def test_lang_code_map_contains_codes():
    from routes.knowledge_base import LANG_CODE_MAP
    assert "ta-IN" in LANG_CODE_MAP
    assert LANG_CODE_MAP["ta-IN"] == "ta"
    assert "en-IN" in LANG_CODE_MAP


def test_lang_name_map_contains_names():
    from routes.knowledge_base import LANG_NAME_MAP
    assert "tamil" in LANG_NAME_MAP
    assert LANG_NAME_MAP["tamil"] == "ta"


def test_clean_crawled_html_basic():
    try:
        from bs4 import BeautifulSoup  # only run if bs4 + lxml are installed
    except ImportError:
        pytest.skip("bs4/lxml not installed")
    from routes.knowledge_base import _clean_crawled_html
    html = "<html><body><p>Hello world this is a test paragraph with enough content.</p></body></html>"
    text, links = _clean_crawled_html(html)
    assert "Hello world" in text
    assert isinstance(links, list)


def test_clean_crawled_html_strips_nav():
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        pytest.skip("bs4/lxml not installed")
    from routes.knowledge_base import _clean_crawled_html
    html = """<html><body>
    <nav>Navigation stuff</nav>
    <main><p>This is the main content paragraph with enough text to be included.</p></main>
    </body></html>"""
    text, _ = _clean_crawled_html(html)
    assert "Navigation" not in text
    assert "main content" in text


def test_clean_crawled_html_collects_internal_links():
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        pytest.skip("bs4/lxml not installed")
    from routes.knowledge_base import _clean_crawled_html
    html = """<html><body>
    <a href="/about">About</a>
    <a href="https://example.com/contact">Contact</a>
    <a href="https://other.com/page">External</a>
    <p>Main content paragraph with enough length to pass the filter check here.</p>
    </body></html>"""
    _, links = _clean_crawled_html(html, base_url="https://example.com")
    assert any("example.com" in l for l in links)
    assert not any("other.com" in l for l in links)


def test_clean_crawled_html_empty():
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        pytest.skip("bs4/lxml not installed")
    from routes.knowledge_base import _clean_crawled_html
    text, links = _clean_crawled_html("")
    assert text == "" or text is not None
    assert isinstance(links, list)


def test_clean_crawled_html_deduplicates():
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        pytest.skip("bs4/lxml not installed")
    from routes.knowledge_base import _clean_crawled_html
    html = """<html><body>
    <p>Duplicate paragraph content that is long enough to pass the filter.</p>
    <p>Duplicate paragraph content that is long enough to pass the filter.</p>
    </body></html>"""
    text, _ = _clean_crawled_html(html)
    assert text.count("Duplicate paragraph") == 1


# ── Routes ───────────────────────────────────────────────────────────────────
def test_list_documents_empty(kb_client):
    client, _ = kb_client
    resp = client.get("/knowledge-base/documents")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_delete_document_not_found(kb_client):
    client, _ = kb_client
    resp = client.delete("/knowledge-base/documents/nonexistent-doc-id")
    assert resp.status_code == 404


def test_save_text_requires_content(kb_client):
    client, _ = kb_client
    with patch('asyncio.create_task'):
        resp = client.post("/knowledge-base/text", json={"title": "Test", "content": ""})
    assert resp.status_code == 400


def test_save_text_success(kb_client, tmp_path):
    client, _ = kb_client
    with patch('routes.knowledge_base.UPLOAD_DIR', tmp_path), \
         patch('asyncio.create_task'):
        resp = client.post("/knowledge-base/text", json={
            "title": "Test Note",
            "content": "This is test content for the knowledge base"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "doc_id" in data
    assert data["status"] == "processing"


def test_search_requires_query(kb_client):
    client, _ = kb_client
    resp = client.post("/knowledge-base/search", json={"query": ""})
    assert resp.status_code == 400


def test_search_returns_results(kb_client):
    client, mock_vs = kb_client
    mock_vs.search = AsyncMock(return_value=["doc1 content", "doc2 content"])
    with patch('routes.knowledge_base.search', AsyncMock(return_value=["doc1 content"])):
        resp = client.post("/knowledge-base/search", json={"query": "test query", "k": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data
    assert "count" in data


def test_search_with_scores(kb_client):
    client, mock_vs = kb_client
    # search_with_scores is imported locally in the route handler, so patch via services.vector_store
    with patch('services.vector_store.search_with_scores',
               AsyncMock(return_value=[("doc1", 0.95)])):
        resp = client.post("/knowledge-base/search", json={
            "query": "test", "include_scores": True
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "documents" in data


def test_translate_text_requires_text(kb_client):
    client, _ = kb_client
    resp = client.post("/knowledge-base/translate", json={"text": "", "target_language": "hi"})
    assert resp.status_code == 400


def test_translate_text_success(kb_client):
    client, _ = kb_client
    mock_translator = MagicMock()
    mock_translator.return_value.translate.return_value = "नमस्ते"
    with patch('deep_translator.GoogleTranslator', mock_translator):
        resp = client.post("/knowledge-base/translate", json={
            "text": "Hello world",
            "target_language": "hi"
        })
    assert resp.status_code == 200
    data = resp.json()
    assert "translated" in data
    assert "target_language" in data


def test_translate_text_failure_500(kb_client):
    client, _ = kb_client
    with patch('deep_translator.GoogleTranslator', side_effect=Exception("API down")):
        resp = client.post("/knowledge-base/translate", json={
            "text": "Hello",
            "target_language": "hi"
        })
    assert resp.status_code == 500


def test_crawl_requires_url(kb_client):
    client, _ = kb_client
    resp = client.post("/knowledge-base/crawl", json={"url": ""})
    assert resp.status_code == 400


def test_upload_unsupported_type(kb_client):
    client, _ = kb_client
    import io
    resp = client.post(
        "/knowledge-base/upload",
        files={"file": ("test.exe", io.BytesIO(b"binary"), "application/octet-stream")},
    )
    assert resp.status_code == 400
