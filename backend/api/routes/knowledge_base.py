import asyncio
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import KnowledgeDocument
from services.ingestion import ingest_file
from services.vector_store import delete_document, get_vector_store, search

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
ALLOWED_TYPES = {"pdf", "xlsx", "xls", "csv"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    suffix = Path(file.filename).suffix.lstrip(".").lower()
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_TYPES}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    doc_id = str(uuid.uuid4())
    dest = UPLOAD_DIR / f"{doc_id}.{suffix}"

    content = await file.read()
    dest.write_bytes(content)

    doc = KnowledgeDocument(id=doc_id, filename=file.filename, file_type=suffix, status="processing")
    db.add(doc)
    await db.commit()

    lang = _detect_language_from_filename(file.filename)
    asyncio.create_task(_run_ingestion(doc_id, str(dest), suffix, db, language=lang))

    return {"doc_id": doc_id, "filename": file.filename, "status": "processing"}


async def _run_ingestion(doc_id: str, file_path: str, file_type: str, db: AsyncSession, language: str = "en"):
    async with db.bind.connect() as conn:
        pass  # use a fresh session
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            chunk_count = await ingest_file(file_path, file_type, doc_id, language=language)
            result = await session.get(KnowledgeDocument, doc_id)
            if result:
                result.status = "ready"
                result.chunk_count = chunk_count
                await session.commit()
        except Exception as e:
            logger.error("Ingestion failed for doc_id=%s: %s", doc_id, e)
            result = await session.get(KnowledgeDocument, doc_id)
            if result:
                result.status = "error"
                result.error_msg = str(e)
                await session.commit()


# Map Sarvam language codes → short language tags stored in ChromaDB
LANG_CODE_MAP = {
    "ta-IN": "ta", "hi-IN": "hi", "te-IN": "te", "kn-IN": "kn",
    "ml-IN": "ml", "mr-IN": "mr", "bn-IN": "bn", "gu-IN": "gu",
    "od-IN": "od", "pa-IN": "pa", "en-IN": "en",
}

# Map language names → short tags (for filename detection)
LANG_NAME_MAP = {
    "tamil": "ta", "hindi": "hi", "telugu": "te", "kannada": "kn",
    "malayalam": "ml", "marathi": "mr", "bengali": "bn", "gujarati": "gu",
    "odia": "od", "punjabi": "pa", "english": "en", "french": "fr",
    "german": "de", "spanish": "es", "arabic": "ar",
}


def _detect_language_from_filename(filename: str) -> str:
    """Extract language tag from filenames like 'doc [Tamil].txt' → 'ta'."""
    import re
    match = re.search(r"\[([^\]]+)\]", filename)
    if match:
        lang_name = match.group(1).lower()
        return LANG_NAME_MAP.get(lang_name, "en")
    return "en"


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()))
    docs = result.scalars().all()
    return [
        {
            "doc_id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "chunk_count": d.chunk_count,
            "status": d.status,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.delete("/documents/{doc_id}")
async def delete_document_route(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    await delete_document(doc_id)
    await db.delete(doc)
    await db.commit()
    return {"deleted": doc_id}


def _clean_crawled_html(html: str, base_url: str = "") -> tuple[str, list[str]]:
    """
    Extract meaningful body text and return (clean_text, internal_links).
    Strips nav/header/footer/scripts and deduplicates lines.
    """
    import re
    from urllib.parse import urljoin, urlparse
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # Collect internal links before stripping the DOM
    internal_links: list[str] = []
    if base_url:
        base_domain = urlparse(base_url).netloc
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Skip anchors, mailto, tel, javascript
            if href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            full = urljoin(base_url, href)
            parsed = urlparse(full)
            # Same domain only, strip fragment
            if parsed.netloc == base_domain:
                clean = parsed._replace(fragment="", query="").geturl()
                internal_links.append(clean)

    # Remove noise tags entirely
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer",
                     "aside", "form", "button", "meta", "link", "img", "svg",
                     "iframe", "video", "audio"]):
        tag.decompose()

    # Remove elements by common class/id patterns for nav/cookie banners/ads
    noise_patterns = re.compile(
        r"(nav|navbar|navigation|breadcrumb|sidebar|footer|header|cookie|"
        r"banner|popup|modal|overlay|advertisement|ad[-_]|social|share|"
        r"menu|topbar|masthead|skip-link)", re.I
    )
    for tag in soup.find_all(True):
        cls = " ".join(tag.get("class", []))
        tid = tag.get("id", "")
        if noise_patterns.search(cls) or noise_patterns.search(tid):
            tag.decompose()

    # Prefer main/article content blocks
    main = (soup.find("main") or soup.find("article")
            or soup.find(id="content")
            or soup.find(class_=re.compile(r"content|main", re.I)))
    root = main if main else soup.body or soup

    # Walk the tree and collect non-empty text lines, deduplicating
    seen: set[str] = set()
    lines: list[str] = []
    for element in root.descendants:
        if element.name in ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li",
                            "td", "th", "dt", "dd", "blockquote", "figcaption"):
            text = element.get_text(" ", strip=True)
            if len(text) < 20:
                continue
            text = re.sub(r"\s+", " ", text).strip()
            if text and text not in seen:
                seen.add(text)
                lines.append(text)

    return "\n\n".join(lines), list(dict.fromkeys(internal_links))


async def _ai_organise(raw_text: str, url: str) -> str:
    """Use GPT-4o-mini to turn messy crawled text into a clean, keyword-rich KB document."""
    import os
    from openai import AsyncOpenAI

    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    system = (
        "You are a knowledge-base formatter for a voice AI receptionist. "
        "Given raw text scraped from a company website, rewrite it as a clean, structured knowledge document "
        "optimised for semantic search and voice Q&A.\n\n"
        "Rules:\n"
        "- PRESERVE ALL factual content — do not summarise or shorten descriptions, keep every detail\n"
        "- Use clear section headings (## About Us, ## Products & Services, ## Contact Info, etc.)\n"
        "- Under each heading write bullet points — keep the full original description for each item\n"
        "- IMPORTANT: Add keyword aliases in parentheses for jargon/brand names so callers find them easily.\n"
        "  Example: '## Products & Services (also called: platforms, solutions, offerings)'\n"
        "  Example: 'Business Enterprise Suite (product, software, tool): AI Readiness Assessment...'\n"
        "- Think about how a caller would ask: 'what products do you have?', 'what services do you offer?',\n"
        "  'tell me about your solutions' — make sure every such question maps to the right section\n"
        "- Only remove: exact duplicates, nav labels, button text (Learn More, Book a Demo), cookie banners, legal boilerplate\n"
        "- Keep everything else: all product names, full descriptions, company info, contact details\n"
        "- Output plain text only — no markdown code blocks, no HTML"
    )
    user = f"Website: {url}\n\nRaw scraped text:\n{raw_text[:20000]}"
    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        organised = resp.choices[0].message.content.strip()
        logger.info("AI organised crawled content: %d chars → %d chars", len(raw_text), len(organised))
        return organised
    except Exception as e:
        logger.warning("AI organisation failed, using raw text: %s", e)
        return raw_text


@router.post("/crawl")
async def crawl_website(body: dict, db: AsyncSession = Depends(get_db)):
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(400, "url is required")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    from langchain_community.document_loaders import WebBaseLoader
    from urllib.parse import urlparse

    doc_id = str(uuid.uuid4())
    hostname = urlparse(url).netloc.replace("www.", "")
    filename = f"{hostname}.txt"

    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        raw_text = "\n".join(d.page_content for d in docs)
        # AI-organise into clean, keyword-rich KB document
        content = await _ai_organise(raw_text, url)
    except Exception as e:
        raise HTTPException(400, f"Failed to fetch URL: {e}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{doc_id}.txt"
    dest.write_text(content, encoding="utf-8")

    doc = KnowledgeDocument(id=doc_id, filename=filename, file_type="txt", status="processing")
    db.add(doc)
    await db.commit()

    asyncio.create_task(_run_ingestion(doc_id, str(dest), "txt", db, language="en"))

    return {"doc_id": doc_id, "filename": filename, "status": "processing"}


@router.post("/text")
async def save_text(body: dict, db: AsyncSession = Depends(get_db)):
    title = (body.get("title") or "Note").strip()
    content = (body.get("content") or "").strip()
    if not content:
        raise HTTPException(400, "content is required")

    doc_id = str(uuid.uuid4())
    filename = f"{title}.txt"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{doc_id}.txt"
    dest.write_text(content, encoding="utf-8")

    doc = KnowledgeDocument(id=doc_id, filename=filename, file_type="note", status="processing")
    db.add(doc)
    await db.commit()

    asyncio.create_task(_run_ingestion(doc_id, str(dest), "txt", db, language="en"))

    return {"doc_id": doc_id, "filename": filename, "status": "processing"}


@router.post("/documents/{doc_id}/translate-to-kb")
async def translate_document_to_kb(doc_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    """Translate an existing KB document into another language using GPT and add it as a new KB entry."""
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    if doc.status != "ready":
        raise HTTPException(400, "Document is not ready yet")

    target_language = (body.get("target_language") or "").strip()
    language_name   = (body.get("language_name") or target_language).strip()
    if not target_language:
        raise HTTPException(400, "target_language is required")

    # Fetch existing chunks from vector store
    store = get_vector_store()
    result = store._collection.get(where={"doc_id": doc_id}, include=["documents"])
    chunks = result.get("documents") or []
    if not chunks:
        raise HTTPException(400, "No content found for this document")

    original_text = "\n\n".join(chunks)

    # Translate using GPT — context-aware, preserves proper nouns
    import os
    from openai import AsyncOpenAI
    oai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    system = (
        f"You are a friendly translator who writes in simple, everyday spoken {language_name} — the kind of language "
        f"a person would naturally use in a phone conversation, not in a formal document.\n"
        "Rules:\n"
        "- Use simple, colloquial words that ordinary people use in daily conversations — NOT formal, literary, or bureaucratic language\n"
        "- Write as if you are a helpful customer service agent speaking on the phone, keeping it warm and natural\n"
        "- Preserve ALL company names, product names, brand names, and technical terms in English (do not translate them)\n"
        "- Keep section headings but translate them in a casual, friendly tone\n"
        "- Short sentences, easy vocabulary — avoid complex grammar structures\n"
        "- Output only the translated text, no explanations"
    )

    try:
        resp = await oai.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=4000,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": original_text[:15000]},
            ],
        )
        translated_text = resp.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {e}")

    # Save as new KB document
    new_doc_id = str(uuid.uuid4())
    base_name  = doc.filename.rsplit(".", 1)[0]
    new_filename = f"{base_name} [{language_name}].txt"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / f"{new_doc_id}.txt"
    dest.write_text(translated_text, encoding="utf-8")

    new_doc = KnowledgeDocument(
        id=new_doc_id, filename=new_filename, file_type="translated", status="processing"
    )
    db.add(new_doc)
    await db.commit()

    # Pass the short language tag so chunks get tagged correctly
    lang_tag = target_language[:2]   # e.g. "ta" from "ta" or "ta-IN"
    asyncio.create_task(_run_ingestion(new_doc_id, str(dest), "translated", db, language=lang_tag))

    logger.info("Translated doc %s → %s (%s, lang=%s)", doc_id, new_doc_id, language_name, lang_tag)
    return {"doc_id": new_doc_id, "filename": new_filename, "status": "processing"}


@router.post("/search")
async def search_knowledge_base(body: dict):
    query = body.get("query", "").strip()
    k = int(body.get("k", 4))
    include_scores = bool(body.get("include_scores", False))
    language = body.get("language") or None   # e.g. "ta", "hi", "en"
    if not query:
        raise HTTPException(400, "query is required")
    if include_scores:
        from services.vector_store import search_with_scores
        results = await search_with_scores(query, k=k, language=language)
        return {
            "documents": [r[0] for r in results],
            "scores": [round(r[1], 4) for r in results],
            "count": len(results),
        }
    results = await search(query, k=k, language=language)
    return {"documents": results, "count": len(results)}


@router.post("/reindex")
async def reindex_all(db: AsyncSession = Depends(get_db)):
    """Re-embed all existing KB documents using the current (multilingual) model.
    Run this once after switching from OpenAI embeddings to local embeddings."""
    from services.vector_store import get_vector_store, rebuild_bm25

    # Clear the v2 collection by deleting and recreating it
    import services.vector_store as vs_module
    store = vs_module.get_vector_store()
    store._client.delete_collection(vs_module.COLLECTION_NAME)
    vs_module._vector_store = None   # reset singleton → recreated fresh on next access
    logger.info("Cleared %s collection for reindex", vs_module.COLLECTION_NAME)

    result = await db.execute(select(KnowledgeDocument).where(KnowledgeDocument.status == "ready"))
    docs = result.scalars().all()

    reindexed, failed = 0, 0
    for doc in docs:
        # Notes and translated docs are written to disk as .txt regardless of file_type
        ext = doc.file_type if doc.file_type not in ("note", "translated") else "txt"
        file_path = UPLOAD_DIR / f"{doc.id}.{ext}"
        if not file_path.exists():
            logger.warning("File missing for doc %s: %s", doc.id, file_path)
            failed += 1
            continue
        lang = _detect_language_from_filename(doc.filename)
        try:
            chunk_count = await ingest_file(str(file_path), doc.file_type, doc.id, language=lang)
            doc.chunk_count = chunk_count
            reindexed += 1
            logger.info("Reindexed %s (%d chunks)", doc.filename, chunk_count)
        except Exception as e:
            logger.error("Reindex failed for %s: %s", doc.filename, e)
            failed += 1

    await db.commit()
    vs_module.rebuild_bm25()
    return {"reindexed": reindexed, "failed": failed, "total": len(docs)}


@router.get("/chunks")
async def get_chunks_by_language(language: str = "en"):
    """Return all stored KB chunks for a given language code (e.g. language=te, hi, en)."""
    store = get_vector_store()
    result = store._collection.get(where={"language": language}, include=["documents"])
    chunks = result.get("documents") or []
    return {"language": language, "chunks": chunks, "count": len(chunks)}


@router.get("/documents/{doc_id}/content")
async def get_document_content(doc_id: str, db: AsyncSession = Depends(get_db)):
    """Return all text chunks stored for a document."""
    doc = await db.get(KnowledgeDocument, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    store = get_vector_store()
    result = store._collection.get(where={"doc_id": doc_id}, include=["documents"])
    chunks = result.get("documents") or []
    return {"doc_id": doc_id, "filename": doc.filename, "chunks": chunks, "chunk_count": len(chunks)}


@router.post("/translate")
async def translate_text(body: dict):
    """Translate text to target language using deep-translator (Google)."""
    text = body.get("text", "").strip()
    target = body.get("target_language", "en").strip()
    if not text:
        raise HTTPException(400, "text is required")
    try:
        from deep_translator import GoogleTranslator
        # Split into chunks of 4500 chars (Google limit is 5000)
        chunk_size = 4500
        parts = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        translated_parts = []
        for part in parts:
            translated = GoogleTranslator(source="auto", target=target).translate(part)
            translated_parts.append(translated or part)
        return {"translated": "\n".join(translated_parts), "target_language": target}
    except Exception as e:
        raise HTTPException(500, f"Translation failed: {str(e)}")
