from typing import Protocol, runtime_checkable
from pydantic import BaseModel
from ..schemas.context import AiRequestContext


class JdAnalysisResult(BaseModel):
    summary: str


class ExperienceResult(BaseModel):
    yaml: str
    fullCvYaml: str


@runtime_checkable
class AIModelClient(Protocol):
    async def analyze_jd(self, context: AiRequestContext) -> JdAnalysisResult:
        """Analyse JD with full context."""
        ...

    async def generate_experience(
        self, analysis: JdAnalysisResult, context: AiRequestContext
    ) -> ExperienceResult:
        """Generate experience section with full context."""
        ...
