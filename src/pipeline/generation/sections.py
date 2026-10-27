"""Generate and guard the probabilistic CV sections."""

from typing import Any, Awaitable, Callable, Dict, List

from pydantic import BaseModel, Field

from ...core.evidence_extractor import EvidenceStore
from ...core.experience_writer import ExperienceWriter
from ...core.jd_analyzer import JDAnalysisOutput
from ...guard.deterministic_guard import DeterministicGuard
from ...llm import LLMProvider
from ...schemas.generation import GenerateCvRequest
from .builder import _stable_id
from .writers import ProjectWriter, SummaryWriter

EmitCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


class GeneratedSections(BaseModel):
    summary: str
    experience_highlights: Dict[str, List[str]] = Field(default_factory=dict)
    project_highlights: Dict[str, List[str]] = Field(default_factory=dict)
    used_evidence_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class SectionGenerator:
    def __init__(self, provider: LLMProvider):
        self.summary_writer = SummaryWriter(provider)
        self.experience_writer = ExperienceWriter(provider)
        self.project_writer = ProjectWriter(provider)

    async def generate(
        self,
        request: GenerateCvRequest,
        jd: JDAnalysisOutput,
        evidence: EvidenceStore,
        knowledge: Dict[str, List[Dict[str, Any]]],
        emit: EmitCallback,
    ) -> GeneratedSections:
        warnings: List[str] = []
        summary_output = await self.summary_writer.write(
            jd, evidence, knowledge["summary"], request.options.language,
        )
        used_ids = list(summary_output.evidence_ids)
        fact_text = " ".join(item.value for item in evidence.items)
        summary_guard = DeterministicGuard.verify(
            summary_output.text, summary_output.evidence_ids, fact_text,
            evidence, request.options.language,
        )
        summary = summary_output.text if summary_guard.is_valid else fact_text[:400]
        if not summary_guard.is_valid:
            warnings.append("Generated summary was rejected by the evidence guard; candidate facts were used.")

        experience_highlights: Dict[str, List[str]] = {}
        for item in request.profile.experiences:
            entry = {
                "id": item.id, "company": item.company, "position": item.position,
                "highlights": item.facts, "start_date": item.start_date,
                "end_date": item.end_date, "date": item.date,
            }
            proposals = await self.experience_writer.rewrite_entry(
                entry, jd, evidence, knowledge["experience"], request.options.language,
            )
            accepted = list(item.facts)
            for proposal in proposals.proposals:
                if proposal.index < 0 or proposal.index >= len(item.facts):
                    continue
                guard = DeterministicGuard.verify(
                    proposal.text, proposal.evidence_ids, item.facts[proposal.index], evidence,
                    request.options.language, item.id,
                    {"start_date": item.start_date, "end_date": item.end_date, "date": item.date},
                )
                if guard.is_valid:
                    accepted[proposal.index] = proposal.text
                    used_ids.extend(proposal.evidence_ids)
                else:
                    warnings.append(f"Rejected ungrounded experience content for {item.id}; original fact retained.")
            experience_highlights[item.id] = accepted
            await emit("partial_update", {
                "section": "experience", "sourceId": item.id, "highlights": accepted,
                "draft": {
                    "id": _stable_id(request.generation_id, "section", "experience"),
                    "title": "Kinh nghiệm" if request.options.language == "vi" else "Experience",
                    "entryType": "Experience",
                    "entries": [{
                        "id": _stable_id(request.generation_id, "experience", item.id),
                        "type": "Experience", "company": item.company,
                        "position": item.position, "highlights": accepted,
                    }],
                },
            })

        project_highlights: Dict[str, List[str]] = {}
        for item in request.profile.projects:
            output = await self.project_writer.write(
                item.id, item.name, item.facts, item.technologies, jd, evidence,
                knowledge["projects"], request.options.language,
            )
            accepted: List[str] = []
            original = " ".join(item.facts + item.technologies)
            for text in output.highlights:
                guard = DeterministicGuard.verify(
                    text, output.evidence_ids, original, evidence,
                    request.options.language, item.id,
                )
                if guard.is_valid:
                    accepted.append(text)
            if len(accepted) != len(output.highlights):
                accepted = list(item.facts)
                warnings.append(f"Rejected ungrounded project content for {item.id}; original facts retained.")
            project_highlights[item.id] = accepted
            used_ids.extend(output.evidence_ids)
            await emit("partial_update", {
                "section": "projects", "sourceId": item.id, "highlights": accepted,
                "draft": {
                    "id": _stable_id(request.generation_id, "section", "projects"),
                    "title": "Dự án" if request.options.language == "vi" else "Projects",
                    "entryType": "Normal",
                    "entries": [{
                        "id": _stable_id(request.generation_id, "project", item.id),
                        "type": "Normal", "name": item.name, "highlights": accepted,
                    }],
                },
            })

        return GeneratedSections(
            summary=summary,
            experience_highlights=experience_highlights,
            project_highlights=project_highlights,
            used_evidence_ids=used_ids,
            warnings=warnings,
        )
