"""Compatibility adapter for the existing POST stream contract."""
from ..jobs.repository import JobRepository
from ..jobs.service import JobService
from ..schemas.generation import GenerateCvRequest


class GenerateService:
    def __init__(self, repository: JobRepository):
        self.repository = repository
        self.jobs = JobService(repository)

    async def create(self, request: GenerateCvRequest):
        return await self.repository.create(request.model_dump(by_alias=True), legacy=True)

    async def stream(self, job_id: str):
        async for event in self.jobs.stream(job_id, legacy=True):
            yield event
