"""Job presentation and durable event subscriptions. No generation tasks here."""
import asyncio
import json
import time

from .contracts import JobView
from .models import TERMINAL_STATUSES
from .repository import JobConflict, JobNotFound, JobRepository


class JobService:
    def __init__(self, repository: JobRepository):
        self.repository = repository

    def view(self, job) -> JobView:
        root = f"/v1/ai/generations/{job.id}"
        return JobView(
            jobId=job.id, requestId=job.request_id, generationId=job.generation_id,
            status=job.status, attempt=job.attempt, lastSequence=job.last_sequence,
            createdAt=job.created_at, deadlineAt=job.deadline_at, startedAt=job.started_at,
            finishedAt=job.finished_at, expiresAt=job.expires_at, error=job.error,
            gaps=job.result.get("gaps", []) if job.result else [],
            statusUrl=root, eventsUrl=f"{root}/events", resultUrl=f"{root}/result",
        )

    async def check_cursor(self, job_id: str, after: int):
        job = await self.repository.get(job_id)
        if after > job.last_sequence:
            raise JobConflict("Event cursor exceeds the last persisted sequence")
        return job

    async def stream(self, job_id: str, *, after: int = 0, legacy: bool = False):
        last_heartbeat = time.monotonic()
        while True:
            # Read status before the batch: concurrent commits cannot make us skip a terminal event.
            try:
                job = await self.repository.get(job_id)
            except JobNotFound:
                # Retention can expire between the initial check and subscribing.
                return
            batch = await self.repository.events(job_id, after)
            for event in batch:
                envelope = {
                    "type": event.type, "requestId": job.request_id,
                    "generationId": job.generation_id, "sequence": event.sequence,
                    "data": event.data,
                }
                if not legacy:
                    envelope.update(jobId=job.id, attempt=event.attempt)
                elif event.type == "error":
                    envelope["data"] = {"message": event.data["message"]}
                encoded = json.dumps(envelope, ensure_ascii=False)
                prefix = "" if legacy else f"id: {event.sequence}\n"
                yield f"{prefix}event: {event.type}\ndata: {encoded}\n\n"
                after = event.sequence
                last_heartbeat = time.monotonic()
            if job.status in TERMINAL_STATUSES and after >= job.last_sequence:
                return
            if batch:
                continue
            if time.monotonic() - last_heartbeat >= self.repository.config.ai_sse_heartbeat_seconds:
                yield ": keep-alive\n\n"
                last_heartbeat = time.monotonic()
            await asyncio.sleep(self.repository.config.ai_sse_poll_seconds)
