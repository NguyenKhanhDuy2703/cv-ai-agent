import os
import sys

import pytest
import pytest_asyncio

from src.jobs.database import configure_event_loop

configure_event_loop()

os.environ["LLM_RETRY_MIN_WAIT"] = "0.001"
os.environ["LLM_RETRY_MAX_WAIT"] = "0.005"

# Ensure pytest runs smoothly even if OS policy blocks binary orjson.pyd
try:
    import orjson  # noqa: F401
except ImportError:
    sys.modules["orjson"] = None


@pytest.fixture
def canonical_en_document():
    from tests.helpers import load_canonical_fixture

    return load_canonical_fixture("en.v1.json")["document"]


@pytest.fixture
def candidate_profile():
    from src.schemas.generation import CandidateProfile
    from tests.helpers import request_payload

    return CandidateProfile.model_validate(request_payload()["profile"])


@pytest_asyncio.fixture
async def job_repository():
    """Integration tests require a disposable local *_test database, never Render."""
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from src.config import Settings
    from src.jobs.database import Database
    from src.jobs.repository import JobRepository

    url = os.environ.get("AI_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set AI_TEST_DATABASE_URL to run PostgreSQL integration tests")
    parsed = make_url(url)
    if parsed.host not in {"localhost", "127.0.0.1", "postgres-test"} or not (parsed.database or "").endswith("_test"):
        pytest.fail("AI_TEST_DATABASE_URL must reference a disposable local *_test database")
    database = Database(url)
    try:
        await database.check_ready()
        async with database.engine.begin() as connection:
            await connection.execute(text("TRUNCATE ai_generation_jobs CASCADE"))
        config = Settings(_env_file=None, AI_PROVIDER="gemini", AI_DATABASE_URL=url,
                          AI_SSE_POLL_SECONDS=0.005, AI_HEARTBEAT_SECONDS=0.05,
                          AI_LEASE_SECONDS=1, AI_WORKER_POLL_SECONDS=0.01)
        yield JobRepository(database, config)
    finally:
        await database.close()

