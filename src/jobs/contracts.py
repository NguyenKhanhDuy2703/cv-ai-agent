"""Public API schemas. No dependency on a consuming application's code."""
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from ..schemas.generation import CandidateProfile, ContractModel, GenerateCvOptions, RenderDefaults


class CreateGenerationRequest(ContractModel):
    request_id: str = Field(alias="requestId", min_length=1)
    job_description: str = Field(default="", alias="jobDescription")
    profile: CandidateProfile
    options: GenerateCvOptions = Field(default_factory=GenerateCvOptions)
    render_defaults: RenderDefaults = Field(alias="renderDefaults")

    @field_validator("request_id")
    @classmethod
    def non_blank_request_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("requestId must not be blank")
        return value.strip()


class JobView(ContractModel):
    job_id: str = Field(alias="jobId")
    request_id: str = Field(alias="requestId")
    generation_id: str = Field(alias="generationId")
    status: Literal["QUEUED", "RUNNING", "NEEDS_INPUT", "COMPLETED", "FAILED"]
    attempt: int
    last_sequence: int = Field(alias="lastSequence")
    created_at: datetime = Field(alias="createdAt")
    deadline_at: datetime = Field(alias="deadlineAt")
    started_at: datetime | None = Field(alias="startedAt")
    finished_at: datetime | None = Field(alias="finishedAt")
    expires_at: datetime | None = Field(alias="expiresAt")
    error: dict[str, str] | None
    gaps: list[dict[str, Any]]
    status_url: str = Field(alias="statusUrl")
    events_url: str = Field(alias="eventsUrl")
    result_url: str = Field(alias="resultUrl")


class JobEventView(ContractModel):
    job_id: str = Field(alias="jobId")
    request_id: str = Field(alias="requestId")
    generation_id: str = Field(alias="generationId")
    sequence: int
    attempt: int
    type: Literal["progress", "gap_report", "partial_update", "needs_input", "done", "error"]
    data: dict[str, Any]
