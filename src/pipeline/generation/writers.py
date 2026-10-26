"""Typed content writers. Knowledge is guidance; candidate evidence is factual input."""

from typing import Any, Dict, List, Optional

from ...core.evidence_extractor import EvidenceStore
from ...core.jd_analyzer import JDAnalysisOutput
from ...llm import LLMProvider
from ...schemas.generation import GeneratedProject, GeneratedSummary


class SummaryWriter:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider
        self.last_error: Optional[str] = None

    async def write(
        self, jd: JDAnalysisOutput, evidence: EvidenceStore,
        knowledge: List[Dict[str, Any]], language: str,
    ) -> GeneratedSummary:
        self.last_error = None
        relevant = [item for item in evidence.items if item.category in {"position", "highlight", "technology"}]
        fallback_items = relevant[:3] or evidence.items[:3]
        fallback_text = " ".join(item.value for item in fallback_items)
        if not fallback_text:
            fallback_text = jd.role_family
        fallback = GeneratedSummary(text=fallback_text, evidenceIds=[item.id for item in fallback_items])
        if self.provider is None:
            return fallback

        messages = [
            {"role": "system", "content": "Write a concise CV summary. Every personal claim must come from CANDIDATE EVIDENCE. JD and GUIDANCE are targeting context only. Return text and evidenceIds."},
            {"role": "user", "content": (
                f"Language: {language}\nTarget role: {jd.role_family}\nJD keywords: {jd.keywords}\n"
                f"CANDIDATE EVIDENCE:\n" + "\n".join(f"[{item.id}] {item.value}" for item in relevant[:30]) +
                "\nGUIDANCE:\n" + "\n".join(str(item.get("content", "")) for item in knowledge)
            )},
        ]
        try:
            return await self.provider.generate_structured(GeneratedSummary, messages)
        except Exception as exc:
            self.last_error = str(exc)
            return fallback


class ProjectWriter:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider
        self.last_error: Optional[str] = None

    async def write(
        self, source_id: str, name: str, facts: List[str], technologies: List[str],
        jd: JDAnalysisOutput, evidence: EvidenceStore, knowledge: List[Dict[str, Any]], language: str,
    ) -> GeneratedProject:
        self.last_error = None
        entry_evidence = [item for item in evidence.items if item.entryId == source_id]
        fallback = GeneratedProject(
            sourceId=source_id,
            highlights=list(facts),
            evidenceIds=[item.id for item in entry_evidence],
        )
        if self.provider is None or not facts:
            return fallback
        messages = [
            {"role": "system", "content": "Rewrite project highlights using only candidate evidence. Do not add skills, metrics, employers, dates, or certifications. Return sourceId, highlights, evidenceIds."},
            {"role": "user", "content": (
                f"Language: {language}\nProject: {name}\nTechnologies supplied by candidate: {technologies}\n"
                f"Target keywords: {jd.keywords}\nCANDIDATE EVIDENCE:\n" +
                "\n".join(f"[{item.id}] {item.value}" for item in entry_evidence) +
                "\nGUIDANCE:\n" + "\n".join(str(item.get("content", "")) for item in knowledge)
            )},
        ]
        try:
            result = await self.provider.generate_structured(GeneratedProject, messages)
            return result if result.source_id == source_id else fallback
        except Exception as exc:
            self.last_error = str(exc)
            return fallback
