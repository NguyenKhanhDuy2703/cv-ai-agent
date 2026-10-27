"""Typed content writers. Knowledge is guidance; candidate evidence is factual input."""

from typing import Any, Dict, List

from ...core.evidence_extractor import EvidenceStore
from ...core.jd_analyzer import JDAnalysisOutput
from ...llm import LLMProvider, LLMSchemaError
from ...llm.operations import GenerationStepError, generate_at_stage, require_provider
from ...schemas.generation import GeneratedProject, GeneratedSummary


class SummaryWriter:
    def __init__(self, provider: LLMProvider):
        self.provider = require_provider(provider)

    async def write(
        self, jd: JDAnalysisOutput, evidence: EvidenceStore,
        knowledge: List[Dict[str, Any]], language: str,
    ) -> GeneratedSummary:
        relevant = [item for item in evidence.items if item.category in {"position", "highlight", "technology"}]
        messages = [
            {"role": "system", "content": "Write a concise CV summary. Every personal claim must come from CANDIDATE EVIDENCE. JD and GUIDANCE are targeting context only. Return text and evidenceIds."},
            {"role": "user", "content": (
                f"Language: {language}\nTarget role: {jd.role_family}\nJD keywords: {jd.keywords}\n"
                f"CANDIDATE EVIDENCE:\n" + "\n".join(f"[{item.id}] {item.value}" for item in relevant[:30]) +
                "\nGUIDANCE:\n" + "\n".join(str(item.get("content", "")) for item in knowledge)
            )},
        ]
        return await generate_at_stage(self.provider, GeneratedSummary, messages, "summary")


class ProjectWriter:
    def __init__(self, provider: LLMProvider):
        self.provider = require_provider(provider)

    async def write(
        self, source_id: str, name: str, facts: List[str], technologies: List[str],
        jd: JDAnalysisOutput, evidence: EvidenceStore, knowledge: List[Dict[str, Any]], language: str,
    ) -> GeneratedProject:
        entry_evidence = [item for item in evidence.items if item.entryId == source_id]
        if not facts:
            return GeneratedProject(sourceId=source_id, highlights=[], evidenceIds=[item.id for item in entry_evidence])
        messages = [
            {"role": "system", "content": "Rewrite project highlights using only candidate evidence. Do not add skills, metrics, employers, dates, or certifications. Return sourceId, highlights, evidenceIds."},
            {"role": "user", "content": (
                f"Language: {language}\nSource ID: {source_id}\nProject: {name}\nTechnologies supplied by candidate: {technologies}\n"
                f"Target keywords: {jd.keywords}\nCANDIDATE EVIDENCE:\n" +
                "\n".join(f"[{item.id}] {item.value}" for item in entry_evidence) +
                "\nGUIDANCE:\n" + "\n".join(str(item.get("content", "")) for item in knowledge)
            )},
        ]
        result = await generate_at_stage(self.provider, GeneratedProject, messages, "projects", source_id)
        if result.source_id != source_id:
            error = LLMSchemaError("Project output sourceId does not match the input")
            raise GenerationStepError("projects", error, GeneratedProject.__name__, source_id) from error
        return result
