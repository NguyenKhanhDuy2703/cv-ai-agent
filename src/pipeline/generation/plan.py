"""Deterministic section and evidence planning."""

from typing import Dict, List

from pydantic import BaseModel, Field

from ...core.evidence_extractor import EvidenceStore
from ...schemas.generation import CandidateProfile


class GenerationPlan(BaseModel):
    section_order: List[str]
    evidence_ids_by_source: Dict[str, List[str]] = Field(default_factory=dict)


def build_generation_plan(profile: CandidateProfile, evidence: EvidenceStore) -> GenerationPlan:
    sections = ["summary"]
    for name, values in (
        ("experience", profile.experiences), ("education", profile.education),
        ("projects", profile.projects), ("skills", profile.skills),
        ("certifications", profile.certifications), ("achievements", profile.achievements),
        ("languages", profile.languages),
    ):
        if values:
            sections.append(name)
    evidence_map: Dict[str, List[str]] = {}
    for item in evidence.items:
        if item.entryId:
            evidence_map.setdefault(item.entryId, []).append(item.id)
    return GenerationPlan(section_order=sections, evidence_ids_by_source=evidence_map)
