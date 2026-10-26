"""Build candidate-only evidence; JD and RAG never enter this store."""

import hashlib
from typing import List

from ...core.evidence_extractor import CandidateEvidence, EvidenceStore, METRIC_REGEX, COMMON_TECH_TOKENS
from ...schemas.generation import CandidateProfile


def build_candidate_evidence(profile: CandidateProfile) -> EvidenceStore:
    items: List[CandidateEvidence] = []
    seen_ids: set[str] = set()

    def add(category: str, value: str, path: str, entry_id: str) -> None:
        value = value.strip()
        if not value:
            return
        digest = hashlib.sha256(f"{entry_id}:{category}:{value}".encode("utf-8")).hexdigest()[:12]
        evidence_id = f"ev-{category[:3]}-{digest}"
        if evidence_id in seen_ids:
            return
        seen_ids.add(evidence_id)
        items.append(CandidateEvidence(
            id=evidence_id, category=category, value=value,
            normalizedValue=value.lower(), sourcePath=path, entryId=entry_id,
        ))

    for idx, exp in enumerate(profile.experiences):
        base = f"profile.experiences[{idx}]"
        add("company", exp.company, f"{base}.company", exp.id)
        add("position", exp.position, f"{base}.position", exp.id)
        if exp.start_date or exp.end_date or exp.date:
            add("date", exp.date or f"{exp.start_date} - {exp.end_date}", f"{base}.dates", exp.id)
        for fact_idx, fact in enumerate(exp.facts):
            add("highlight", fact, f"{base}.facts[{fact_idx}]", exp.id)
            for metric in METRIC_REGEX.findall(fact):
                add("metric", metric, f"{base}.facts[{fact_idx}]", exp.id)
            for token in fact.lower().split():
                clean = token.strip(".,:;()[]")
                if clean in COMMON_TECH_TOKENS:
                    add("technology", clean, f"{base}.facts[{fact_idx}]", exp.id)

    for idx, project in enumerate(profile.projects):
        base = f"profile.projects[{idx}]"
        add("company", project.name, f"{base}.name", project.id)
        for tech in project.technologies:
            add("technology", tech, f"{base}.technologies", project.id)
        for fact_idx, fact in enumerate(project.facts):
            add("highlight", fact, f"{base}.facts[{fact_idx}]", project.id)
            for metric in METRIC_REGEX.findall(fact):
                add("metric", metric, f"{base}.facts[{fact_idx}]", project.id)

    for idx, education in enumerate(profile.education):
        base = f"profile.education[{idx}]"
        add("company", education.institution, f"{base}.institution", education.id)
        add("position", education.degree, f"{base}.degree", education.id)
        for fact_idx, fact in enumerate(education.facts):
            add("highlight", fact, f"{base}.facts[{fact_idx}]", education.id)

    for group_name in ("skills", "certifications", "achievements", "languages"):
        for idx, item in enumerate(getattr(profile, group_name)):
            category = "technology" if group_name == "skills" else "highlight"
            add(category, " ".join(filter(None, (item.name, item.details))), f"profile.{group_name}[{idx}]", item.id)

    return EvidenceStore(items=items)
