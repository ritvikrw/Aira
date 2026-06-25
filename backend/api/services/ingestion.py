import os
import logging
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, UnstructuredExcelLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.vector_store import add_documents

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=400,
    chunk_overlap=50,
    separators=["\n\n", "\n", ". ", " ", ""],
)


async def ingest_file(file_path: str, file_type: str, doc_id: str, language: str = "en") -> int:
    """Load a file, chunk it, embed into ChromaDB with a language tag.
    Returns the number of chunks stored."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type == "pdf":
        loader = PyPDFLoader(str(path))
    elif file_type in ("xlsx", "xls"):
        loader = UnstructuredExcelLoader(str(path), mode="elements")
    elif file_type == "csv":
        loader = CSVLoader(str(path))
    elif file_type in ("txt", "note", "translated"):
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    logger.info("Loading %s (type=%s, doc_id=%s, lang=%s)", path.name, file_type, doc_id, language)
    raw_docs = loader.load()

    chunks = _splitter.split_documents(raw_docs)

    for chunk in chunks:
        chunk.metadata.setdefault("source", path.name)
        chunk.metadata["doc_id"] = doc_id
        chunk.metadata["language"] = language

    count = await add_documents(chunks, doc_id)
    logger.info("Stored %d chunks for doc_id=%s (lang=%s)", count, doc_id, language)
    return count
