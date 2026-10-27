"""Atomic PostgreSQL job operations. Never hold locks while calling a model."""
import hashlib
import json
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError

from ..config import Settings
from ..schemas.generation import GenerateCvRequest, GenerateCvResult, GenerationReport
from .database import Database
from .models import GenerationEvent, GenerationJob, TERMINAL_STATUSES


class JobNotFound(Exception):
    pass


class JobConflict(Exception):
    pass


class LeaseLost(Exception):
    pass


def normalize(value):
    """Trim input boundaries, preserving facts, list order and interior text."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


class JobRepository:
    def __init__(self, database: Database, config: Settings):
        self.database = database
        self.config = config

    async def create(self, payload: dict, *, legacy: bool = False) -> GenerationJob:
        normalized = normalize(payload)
        request_id = normalized["requestId"]
        if not request_id:
            raise JobConflict("requestId must not be blank")
        legacy_id = normalized.pop("generationId", None)
        if legacy and not legacy_id:
            raise JobConflict("generationId must not be blank")
        fingerprint = hashlib.sha256(json.dumps(
            normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode()).hexdigest()

        def verify(existing):
            if existing.input_hash != fingerprint or (legacy and existing.generation_id != legacy_id):
                raise JobConflict("requestId already belongs to different input")
            return existing

        try:
            async with self.database.sessions.begin() as session:
                # Retention and idempotency use the same boundary even before cleanup runs.
                await session.execute(delete(GenerationJob).where(
                    GenerationJob.request_id == request_id,
                    GenerationJob.expires_at <= func.clock_timestamp(),
                ))
                existing = await session.scalar(select(GenerationJob).where(
                    GenerationJob.request_id == request_id,
                ))
                if existing:
                    return verify(existing)
                now = await session.scalar(select(func.clock_timestamp()))
                job_id = str(uuid4())
                generation_id = legacy_id if legacy else job_id
                request = GenerateCvRequest.model_validate({**normalized, "generationId": generation_id})
                job = GenerationJob(
                    id=job_id, request_id=request_id, generation_id=generation_id,
                    input_hash=fingerprint, input_snapshot=request.model_dump(by_alias=True),
                    status="QUEUED", attempt=0, last_sequence=0, created_at=now,
                    deadline_at=now + timedelta(seconds=self.config.ai_job_timeout_seconds),
                )
                session.add(job)
                await session.flush()
                return job
        except IntegrityError:
            # A concurrent creator can win either unique constraint.
            try:
                existing = await self.by_request_id(request_id)
            except JobNotFound:
                raise JobConflict("generationId already belongs to another request") from None
            return verify(existing)

    async def by_request_id(self, request_id: str) -> GenerationJob:
        async with self.database.sessions() as session:
            job = await session.scalar(select(GenerationJob).where(
                GenerationJob.request_id == request_id,
                or_(GenerationJob.expires_at.is_(None), GenerationJob.expires_at > func.clock_timestamp()),
            ))
            if job is None:
                raise JobNotFound()
            return job

    async def get(self, job_id: str) -> GenerationJob:
        async with self.database.sessions() as session:
            row = (await session.execute(select(
                GenerationJob, GenerationJob.deadline_at <= func.clock_timestamp(),
            ).where(
                GenerationJob.id == job_id,
                or_(GenerationJob.expires_at.is_(None), GenerationJob.expires_at > func.clock_timestamp()),
            ))).first()
            if row is None:
                raise JobNotFound()
            job, overdue = row
        if overdue and job.status not in TERMINAL_STATUSES:
            return await self._expire_deadline(job_id)
        return job

    async def _expire_deadline(self, job_id: str) -> GenerationJob:
        # Status/SSE must settle a passed deadline even when every worker is down.
        # Most reads remain lock-free; only overdue jobs need a short write lock.
        async with self.database.sessions.begin() as session:
            job = await session.scalar(select(GenerationJob).where(
                GenerationJob.id == job_id,
                GenerationJob.status.in_(["QUEUED", "RUNNING"]),
                GenerationJob.deadline_at <= func.clock_timestamp(),
            ).with_for_update())
            if job is not None:
                now = await session.scalar(select(func.clock_timestamp()))
                error = {"code": "GENERATION_TIMEOUT", "message": "Generation deadline exceeded"}
                self._terminal(session, job, self._failed_result(job), now, error)
                return job
        # Another writer may have finished while this request was acquiring the lock.
        return await self.get(job_id)

    async def events(self, job_id: str, after: int, limit: int = 100) -> list[GenerationEvent]:
        async with self.database.sessions() as session:
            return list((await session.scalars(select(GenerationEvent).where(
                GenerationEvent.job_id == job_id, GenerationEvent.sequence > after,
            ).order_by(GenerationEvent.sequence).limit(limit))).all())

    def _event(self, session, job: GenerationJob, event_type: str, data: dict, now) -> None:
        job.last_sequence += 1
        session.add(GenerationEvent(
            job_id=job.id, sequence=job.last_sequence, attempt=job.attempt,
            type=event_type, data=data, created_at=now,
        ))

    def _terminal(self, session, job, result: GenerateCvResult, now, error=None) -> None:
        event_type = {"needs_input": "needs_input", "failed": "error"}.get(result.status, "done")
        job.status = {"needs_input": "NEEDS_INPUT", "failed": "FAILED"}.get(result.status, "COMPLETED")
        job.result = result.model_dump(by_alias=True)
        job.error = error
        job.finished_at = now
        job.expires_at = now + timedelta(hours=self.config.ai_retention_hours)
        job.lease_token = None
        job.lease_expires_at = None
        data = {"message": error["message"] if error else "Generation failed"} if event_type == "error" else job.result
        self._event(session, job, event_type, data, now)

    def _failed_result(self, job) -> GenerateCvResult:
        return GenerateCvResult(status="failed", report=GenerationReport(
            requestId=job.request_id, generationId=job.generation_id,
        ))

    async def maintain(self) -> None:
        async with self.database.sessions.begin() as session:
            now = await session.scalar(select(func.clock_timestamp()))
            await session.execute(delete(GenerationJob).where(GenerationJob.expires_at <= now))
            jobs = (await session.scalars(select(GenerationJob).where(
                GenerationJob.status.in_(["QUEUED", "RUNNING"]),
                or_(GenerationJob.deadline_at <= now,
                    (GenerationJob.status == "RUNNING") & (GenerationJob.lease_expires_at <= now)),
            ).order_by(GenerationJob.created_at).limit(100).with_for_update(skip_locked=True))).all()
            for job in jobs:
                if job.deadline_at <= now:
                    error = {"code": "GENERATION_TIMEOUT", "message": "Generation deadline exceeded"}
                    self._terminal(session, job, self._failed_result(job), now, error)
                elif job.attempt >= self.config.ai_job_max_attempts:
                    error = {"code": "ATTEMPTS_EXHAUSTED", "message": "Generation worker recovery exhausted"}
                    self._terminal(session, job, self._failed_result(job), now, error)
                else:
                    job.status = "QUEUED"
                    job.lease_token = None
                    job.lease_expires_at = None

    async def claim(self) -> GenerationJob | None:
        async with self.database.sessions.begin() as session:
            now = await session.scalar(select(func.clock_timestamp()))
            job = await session.scalar(select(GenerationJob).where(
                GenerationJob.status == "QUEUED", GenerationJob.deadline_at > now,
                GenerationJob.attempt < self.config.ai_job_max_attempts,
            ).order_by(GenerationJob.created_at, GenerationJob.id).limit(1).with_for_update(skip_locked=True))
            if job is None:
                return None
            job.status = "RUNNING"
            job.attempt += 1
            job.lease_token = str(uuid4())
            job.lease_expires_at = now + timedelta(seconds=self.config.ai_lease_seconds)
            if job.started_at is None:
                job.started_at = now
            await session.flush()
            return job

    async def _owned(self, session, job_id, token):
        job = await session.scalar(select(GenerationJob).where(
            GenerationJob.id == job_id,
        ).with_for_update())
        now = await session.scalar(select(func.clock_timestamp()))
        if (job is None or job.status != "RUNNING" or job.lease_token != token
                or job.lease_expires_at <= now or job.deadline_at <= now):
            raise LeaseLost()
        return job, now

    async def heartbeat(self, job_id: str, token: str) -> None:
        async with self.database.sessions.begin() as session:
            job, now = await self._owned(session, job_id, token)
            job.lease_expires_at = now + timedelta(seconds=self.config.ai_lease_seconds)

    async def append(self, job_id: str, token: str, event: dict) -> None:
        if event["type"] not in {"progress", "gap_report", "partial_update"}:
            raise ValueError("Pipeline emitted an unsupported event")
        async with self.database.sessions.begin() as session:
            job, now = await self._owned(session, job_id, token)
            self._event(session, job, event["type"], event["data"], now)

    async def finish(self, job_id: str, token: str, result: GenerateCvResult, error=None) -> None:
        async with self.database.sessions.begin() as session:
            job, now = await self._owned(session, job_id, token)
            self._terminal(session, job, result, now, error)

    async def fail(self, job_id: str, token: str, code: str, message: str) -> None:
        job = await self.get(job_id)
        await self.finish(job_id, token, self._failed_result(job), {"code": code, "message": message})

    async def release(self, job_id: str, token: str) -> None:
        async with self.database.sessions.begin() as session:
            job, now = await self._owned(session, job_id, token)
            # Recovery is handled by the same bounded lease-recovery path.
            job.lease_expires_at = now
