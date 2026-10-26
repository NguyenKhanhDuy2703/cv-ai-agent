"""Deterministic canonical RenderCV document builder."""

from typing import Any, Dict, Iterable, List
from uuid import NAMESPACE_URL, uuid5

from ...schemas.generation import CandidateListItem, GenerateCvRequest


def _stable_id(generation_id: str, kind: str, source_id: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"cv-generation:{generation_id}:{kind}:{source_id}"))


def _clean(mapping: Dict[str, Any]) -> Dict[str, Any]:
    required = {"company", "position", "institution", "area", "degree", "name"}
    return {key: value for key, value in mapping.items() if key in required or value not in (None, "")}


def _bullet_section(request: GenerateCvRequest, key: str, title: str, items: Iterable[CandidateListItem]) -> Dict[str, Any]:
    entries = []
    for item in items:
        text = " — ".join(value for value in (item.name, item.details, item.date) if value)
        entries.append({"id": _stable_id(request.generation_id, key, item.id), "type": "Bullet", "bullet": text})
    return {"id": _stable_id(request.generation_id, "section", key), "title": title, "entryType": "Bullet", "entries": entries}


def build_canonical_document(
    request: GenerateCvRequest,
    summary: str,
    experience_highlights: Dict[str, List[str]],
    project_highlights: Dict[str, List[str]],
    ordered_skills: List[CandidateListItem] | None = None,
) -> Dict[str, Any]:
    profile = request.profile
    language = request.options.language
    titles = {
        "summary": "Tóm tắt" if language == "vi" else "Summary",
        "experience": "Kinh nghiệm" if language == "vi" else "Experience",
        "education": "Học vấn" if language == "vi" else "Education",
        "projects": "Dự án" if language == "vi" else "Projects",
        "skills": "Kỹ năng" if language == "vi" else "Skills",
        "certifications": "Chứng chỉ" if language == "vi" else "Certifications",
        "achievements": "Thành tích" if language == "vi" else "Achievements",
        "languages": "Ngôn ngữ" if language == "vi" else "Languages",
    }
    sections: List[Dict[str, Any]] = []
    if summary:
        sections.append({
            "id": _stable_id(request.generation_id, "section", "summary"), "title": titles["summary"],
            "entryType": "Text", "entries": [{"id": _stable_id(request.generation_id, "summary", "main"), "type": "Text", "text": summary}],
        })
    if profile.experiences:
        sections.append({
            "id": _stable_id(request.generation_id, "section", "experience"), "title": titles["experience"], "entryType": "Experience",
            "entries": [_clean({
                "id": _stable_id(request.generation_id, "experience", item.id), "type": "Experience",
                "company": item.company, "position": item.position,
                "highlights": experience_highlights.get(item.id, item.facts), "date": item.date,
                "start_date": item.start_date, "end_date": item.end_date, "location": item.location,
            }) for item in profile.experiences],
        })
    if profile.education:
        sections.append({
            "id": _stable_id(request.generation_id, "section", "education"), "title": titles["education"], "entryType": "Education",
            "entries": [_clean({
                "id": _stable_id(request.generation_id, "education", item.id), "type": "Education",
                "institution": item.institution, "area": item.area, "degree": item.degree,
                "highlights": item.facts, "date": item.date, "start_date": item.start_date,
                "end_date": item.end_date, "location": item.location,
            }) for item in profile.education],
        })
    if profile.projects:
        sections.append({
            "id": _stable_id(request.generation_id, "section", "projects"), "title": titles["projects"], "entryType": "Normal",
            "entries": [_clean({
                "id": _stable_id(request.generation_id, "project", item.id), "type": "Normal", "name": item.name,
                "highlights": project_highlights.get(item.id, item.facts), "summary": item.url,
            }) for item in profile.projects],
        })
    for key, items in (
        ("skills", ordered_skills if ordered_skills is not None else profile.skills), ("certifications", profile.certifications),
        ("achievements", profile.achievements), ("languages", profile.languages),
    ):
        if items:
            sections.append(_bullet_section(request, key, titles[key], items))

    cv = {
        "name": profile.name,
        "headline": profile.target_position,
        "location": profile.location,
        "email": profile.email,
        "phone": profile.phone,
        "website": profile.website,
        "photo_url": profile.photo_url,
        "social_networks": [
            {"id": _stable_id(request.generation_id, "social", item.id), "network": item.network, "username": item.username}
            for item in profile.social_networks
        ],
        "custom_connections": [],
        "sections": sections,
    }
    return {
        "cv": cv,
        "design": request.render_defaults.design,
        "locale": request.render_defaults.locale,
        "settings": request.render_defaults.settings,
    }
