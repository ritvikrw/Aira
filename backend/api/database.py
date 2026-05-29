import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://recep:recep@localhost:5432/recep")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Idempotent migrations for columns added after initial schema
        await conn.execute(text(
            "ALTER TABLE call_logs ADD COLUMN IF NOT EXISTS caller_name VARCHAR(256)"
        ))
        await conn.execute(text(
            "ALTER TABLE call_summaries ADD COLUMN IF NOT EXISTS call_category VARCHAR(64)"
        ))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS agent_settings (
                key   VARCHAR(64) PRIMARY KEY,
                value TEXT NOT NULL
            )
        """))
        await conn.execute(text(
            "ALTER TABLE call_metrics ADD COLUMN IF NOT EXISTS stt_ttft_ms FLOAT"
        ))
