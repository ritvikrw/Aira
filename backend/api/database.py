import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://recep:recep@localhost:5432/recep")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,       # test connection before handing it out
    pool_size=5,              # keep 5 persistent connections
    max_overflow=10,          # allow up to 10 extra under load
    pool_recycle=300,         # recycle connections every 5 min to avoid stale TCP
    pool_timeout=30,          # wait up to 30s for a free connection
    connect_args={"timeout": 10},  # asyncpg connect timeout per attempt
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def _add_column_if_missing(conn, table: str, column: str, col_type: str) -> None:
    """Dialect-safe idempotent column migration (works on both SQLite and PostgreSQL)."""
    is_sqlite = DATABASE_URL.startswith("sqlite")
    if is_sqlite:
        result = await conn.execute(text(f"PRAGMA table_info({table})"))
        cols = [row[1] for row in result.fetchall()]
    else:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :t AND table_schema = 'public'"
        ), {"t": table})
        cols = [row[0] for row in result.fetchall()]
    if column not in cols:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent migrations for columns added after initial schema
        await _add_column_if_missing(conn, "call_logs",      "caller_name",   "VARCHAR(256)")
        await _add_column_if_missing(conn, "call_summaries", "call_category", "VARCHAR(64)")
        await _add_column_if_missing(conn, "call_metrics",   "stt_ttft_ms",   "FLOAT")
