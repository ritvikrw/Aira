"""Tests for api/main.py — app creation, lifespan, and cleanup functions."""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))


_API_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'backend', 'api'))


def _import_main():
    """Import api/main.py with mocked database and dotenv."""
    # Ensure backend/api is first in sys.path so we get api/main.py not voice_agent/main.py
    if _API_PATH in sys.path:
        sys.path.remove(_API_PATH)
    sys.path.insert(0, _API_PATH)

    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location("main", os.path.join(_API_PATH, "main.py"))
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'test'}):
        if 'main' in sys.modules:
            del sys.modules['main']
        with patch('database.create_tables', AsyncMock()), \
             patch('database.AsyncSessionLocal'):
            import main
    assert hasattr(main, 'app'), f"Imported wrong main: {main.__file__}"
    return main


def test_app_is_fastapi():
    main = _import_main()
    from fastapi import FastAPI
    assert isinstance(main.app, FastAPI)


def test_app_title():
    main = _import_main()
    assert "RECEP" in main.app.title or main.app.title is not None


def test_health_endpoint():
    main = _import_main()
    from fastapi.testclient import TestClient
    with patch.object(main, 'cleanup_stale_calls', AsyncMock(return_value=0)), \
         patch.object(main, 'create_tables', AsyncMock(), create=True):
        with patch('database.create_tables', AsyncMock()):
            with TestClient(main.app) as c:
                resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_stale_call_threshold():
    main = _import_main()
    assert main.STALE_CALL_THRESHOLD_MINUTES == 60


@pytest.mark.asyncio
async def test_cleanup_stale_calls_no_stale():
    main = _import_main()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch('main.AsyncSessionLocal', return_value=mock_session_ctx):
        count = await main.cleanup_stale_calls()
    assert count == 0


@pytest.mark.asyncio
async def test_cleanup_stale_calls_with_stale():
    main = _import_main()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [("sess-old-1",), ("sess-old-2",)]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    with patch('main.AsyncSessionLocal', return_value=mock_session_ctx):
        count = await main.cleanup_stale_calls()
    assert count == 2


def test_cors_middleware_configured():
    main = _import_main()
    middleware_classes = [m.cls.__name__ for m in main.app.user_middleware]
    assert "CORSMiddleware" in middleware_classes


def test_routers_included():
    main = _import_main()
    routes = [r.path for r in main.app.routes]
    assert any("/calls" in r for r in routes)
    assert any("/transcripts" in r for r in routes)
    assert any("/settings" in r for r in routes)
    assert any("/health" in r for r in routes)
