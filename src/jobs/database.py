"""Explicit database lifecycle, shared by API, worker and migrations."""
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import SCHEMA_REVISION


def database_url(value: str) -> str:
    if not value:
        raise ValueError("AI_DATABASE_URL is required for the AI API and worker")
    url = make_url(value)
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("AI_DATABASE_URL must use PostgreSQL with psycopg")
    return url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


def configure_event_loop() -> None:
    # Psycopg async connections require SelectorEventLoop on Windows.
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class Database:
    def __init__(self, url: str):
        self.engine = create_async_engine(
            database_url(url), pool_pre_ping=True, hide_parameters=True,
            connect_args={"connect_timeout": 5},
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def check_ready(self) -> None:
        async with self.engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            if revision != SCHEMA_REVISION:
                raise RuntimeError("AI database migrations must be upgraded before startup")
            await connection.execute(text("SELECT id FROM ai_generation_jobs LIMIT 0"))
            await connection.execute(text("SELECT id FROM ai_generation_events LIMIT 0"))

    async def close(self) -> None:
        await self.engine.dispose()
