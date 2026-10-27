"""Test-only process entrypoint injecting fake inference, never a production mode."""
import asyncio

from src.jobs.database import configure_event_loop
from src.worker import main
from tests.providers import make_pipeline

if __name__ == "__main__":
    configure_event_loop()
    asyncio.run(main(make_pipeline))
