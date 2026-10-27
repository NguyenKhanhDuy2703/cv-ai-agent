"""Acceptance with independent OS processes, HTTP and a disposable PostgreSQL."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from uuid import uuid4

import httpx
import pytest

from tests.helpers import request_payload

pytestmark = [pytest.mark.postgres, pytest.mark.asyncio]
ROOT = Path(__file__).resolve().parents[1]


async def stop_process(process):
    if process.poll() is None:
        process.kill()
    await asyncio.to_thread(process.wait, timeout=10)


async def wait_for(operation, predicate, timeout=15):
    async with asyncio.timeout(timeout):
        while True:
            try:
                value = await operation()
                if predicate(value):
                    return value
            except httpx.TransportError:
                pass
            await asyncio.sleep(0.03)


async def test_http_job_survives_hard_worker_and_api_restarts(job_repository, tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = {**os.environ, "AI_DATABASE_URL": job_repository.config.ai_database_url,
           "AI_PROVIDER": "gemini", "AI_PORT": str(port), "AI_SECRET_KEY": "process-test-token",
           "AI_LEASE_SECONDS": "0.5", "AI_HEARTBEAT_SECONDS": "0.1",
           "AI_WORKER_POLL_SECONDS": "0.02", "AI_SSE_POLL_SECONDS": "0.01",
           "AI_JOB_TIMEOUT_SECONDS": "30"}
    processes = []
    log_path = tmp_path / "service-processes.log"
    with log_path.open("w", encoding="utf-8") as log:
        def start(*args):
            process = subprocess.Popen(
                [sys.executable, "-B", *args], cwd=ROOT, env=env,
                stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            processes.append(process)
            return process

        headers = {"Authorization": "Bearer process-test-token"}
        base_url = f"http://127.0.0.1:{port}"
        try:
            api = start("-m", "src.main")
            async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=2) as client:
                await wait_for(lambda: client.get("/health/ready"), lambda response: response.status_code == 200)
                payload = request_payload(requestId=str(uuid4()))
                payload.pop("generationId")
                response = await client.post("/v1/ai/generations", json=payload)
                assert response.status_code == 202
                job = response.json()
                paused_code = '''
import asyncio
from src.config import settings
from src.jobs.database import Database, configure_event_loop
from src.jobs.repository import JobRepository
from src.worker import GenerationWorker
class Paused:
    async def generate(self, request, on_event):
        await on_event({"type":"progress", "data":{"step":"paused", "message":"Processing."}})
        await asyncio.sleep(60)
async def main():
    database = Database(settings.ai_database_url)
    try:
        await database.check_ready()
        await GenerationWorker(JobRepository(database, settings), Paused).run(asyncio.Event())
    finally:
        await database.close()
configure_event_loop()
asyncio.run(main())
'''
                crashed_worker = start("-c", paused_code)
                await wait_for(lambda: client.get(job["statusUrl"]), lambda r: r.json().get("lastSequence", 0) > 0)
                # Close a real HTTP SSE subscription while the worker is paused.
                async with client.stream("GET", job["eventsUrl"]) as stream:
                    async for line in stream.aiter_lines():
                        if line.startswith("data:"):
                            assert json.loads(line[5:])["attempt"] == 1
                            break
                assert (await client.get(job["statusUrl"])).json()["status"] == "RUNNING"
                await stop_process(crashed_worker)
                await stop_process(api)

            # Fresh API/worker processes know only persisted database state.
            start("-m", "src.main")
            start("-m", "tests.worker_process")
            async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=2) as client:
                await wait_for(lambda: client.get("/health/ready"), lambda r: r.status_code == 200)
                finished = await wait_for(lambda: client.get(job["statusUrl"]),
                                          lambda r: r.json().get("status") in {"COMPLETED", "FAILED"})
                assert finished.json()["status"] == "COMPLETED", log_path.read_text(encoding="utf-8")
                assert finished.json()["attempt"] == 2
                result = (await client.get(job["resultUrl"])).json()
                assert result["document"]["cv"]["name"] == payload["profile"]["name"]
                assert result["report"]["generationId"] == job["generationId"]
                replay = await client.get(job["eventsUrl"], headers={"Last-Event-ID": "1"})
                assert replay.text.startswith("id: 2\n")
                assert replay.text.count("event: done") == 1
                assert '"attempt": 2' in replay.text
        finally:
            for process in reversed(processes):
                await stop_process(process)


async def test_migration_round_trip_on_isolated_database(job_repository):
    await job_repository.database.close()
    env = {**os.environ, "AI_DATABASE_URL": job_repository.config.ai_database_url, "AI_PROVIDER": "gemini"}
    for target in ("base", "head"):
        result = await asyncio.to_thread(
            subprocess.run, [sys.executable, "-B", "-m", "alembic", "downgrade" if target == "base" else "upgrade", target],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=20,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        assert result.returncode == 0, result.stderr
    await job_repository.database.check_ready()
