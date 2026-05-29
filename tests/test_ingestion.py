"""Tests for services/ingestion.py."""
import sys
import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api', 'services'))

# Langchain stubs — get existing ones from conftest.py or create new (force-set to ensure consistency)
_lc_community = MagicMock()
_lc_splitter = MagicMock()
sys.modules['langchain_community'] = _lc_community
sys.modules['langchain_community.document_loaders'] = _lc_community.document_loaders
sys.modules['langchain_text_splitters'] = _lc_splitter

# Stub vector_store so ingestion can import it without real sentence_transformers
_mock_vs = MagicMock()
_mock_vs.add_documents = AsyncMock(return_value=0)
sys.modules['services.vector_store'] = _mock_vs


def _import_ingestion():
    if 'ingestion' in sys.modules:
        del sys.modules['ingestion']
    mock_splitter = MagicMock()
    mock_splitter.split_documents = MagicMock(return_value=[])
    _lc_splitter.RecursiveCharacterTextSplitter.return_value = mock_splitter
    import ingestion
    return ingestion, mock_splitter


@pytest.mark.asyncio
async def test_ingest_file_not_found():
    ingestion, _ = _import_ingestion()
    with pytest.raises(FileNotFoundError):
        await ingestion.ingest_file("/nonexistent/path.pdf", "pdf", "doc-1")


@pytest.mark.asyncio
async def test_ingest_file_unsupported_type(tmp_path):
    ingestion, _ = _import_ingestion()
    f = tmp_path / "test.docx"
    f.write_bytes(b"content")
    with pytest.raises(ValueError, match="Unsupported"):
        await ingestion.ingest_file(str(f), "docx", "doc-1")


@pytest.mark.asyncio
async def test_ingest_txt_file(tmp_path):
    ingestion, mock_splitter = _import_ingestion()
    txt = tmp_path / "test.txt"
    txt.write_text("Hello world content", encoding="utf-8")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.TextLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(txt), "txt", "doc-txt", language="en")
    assert count == 1
    assert mock_doc.metadata["doc_id"] == "doc-txt"
    assert mock_doc.metadata["language"] == "en"


@pytest.mark.asyncio
async def test_ingest_pdf_file(tmp_path):
    ingestion, mock_splitter = _import_ingestion()
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF content")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.PyPDFLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(pdf), "pdf", "doc-pdf", language="en")
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_csv_file(tmp_path):
    ingestion, mock_splitter = _import_ingestion()
    csv = tmp_path / "test.csv"
    csv.write_text("a,b\n1,2", encoding="utf-8")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.CSVLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(csv), "csv", "doc-csv")
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_xlsx_file(tmp_path):
    ingestion, mock_splitter = _import_ingestion()
    xlsx = tmp_path / "test.xlsx"
    xlsx.write_bytes(b"PK content")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.UnstructuredExcelLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(xlsx), "xlsx", "doc-xlsx")
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_note_type(tmp_path):
    """'note' file type should use TextLoader."""
    ingestion, mock_splitter = _import_ingestion()
    note = tmp_path / "mynote.txt"
    note.write_text("Note content", encoding="utf-8")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.TextLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(note), "note", "doc-note")
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_translated_type(tmp_path):
    """'translated' file type should use TextLoader."""
    ingestion, mock_splitter = _import_ingestion()
    f = tmp_path / "translated.txt"
    f.write_text("Translated content", encoding="utf-8")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.TextLoader', return_value=mock_loader):
        count = await ingestion.ingest_file(str(f), "translated", "doc-trans", language="te")
    assert count == 1


@pytest.mark.asyncio
async def test_ingest_sets_source_metadata(tmp_path):
    ingestion, mock_splitter = _import_ingestion()
    f = tmp_path / "myfile.txt"
    f.write_text("content", encoding="utf-8")

    mock_doc = MagicMock()
    mock_doc.metadata = {}
    mock_loader = MagicMock()
    mock_loader.load.return_value = [mock_doc]
    mock_splitter.split_documents.return_value = [mock_doc]

    with patch('ingestion.add_documents', AsyncMock(return_value=1)), \
         patch('ingestion.TextLoader', return_value=mock_loader):
        await ingestion.ingest_file(str(f), "txt", "doc-src", language="hi")

    assert mock_doc.metadata["source"] == "myfile.txt"
    assert mock_doc.metadata["doc_id"] == "doc-src"
    assert mock_doc.metadata["language"] == "hi"
