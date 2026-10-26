"""
Candidate Evidence Extractor.

Extracts authoritative facts from candidate's RenderCV canonical document:
- Companies, positions, dates
- Exact bullets/highlights
- Metrics and numbers (percentages, counts, currencies, multipliers, versions)
- Technology and skill tokens

Every evidence piece has a stable deterministic ID and exact sourcePath.
"""
import hashlib
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

# Regex to capture numbers with units/percentages/multipliers: e.g. "99.99%", "$2M", "50+", "10x", "30"
METRIC_REGEX = re.compile(
    r"(?:\$|€|£)?\b\d+(?:[.,]\d+)?(?:%|\+|x|k|m|b|ms|s|gb|tb|req/s|rps)?\b",
    re.IGNORECASE,
)

# Common tech tokens regex for quick candidate extraction
COMMON_TECH_TOKENS = {
    "python", "java", "golang", "go", "c++", "c#", "rust", "typescript", "javascript",
    "react", "vue", "angular", "next.js", "nestjs", "fastapi", "django", "flask",
    "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "k8s", "aws", "gcp", "azure", "ci/cd", "git", "linux",
    "kafka", "rabbitmq", "graphql", "rest", "grpc", "terraform", "helm", "spark",
    "pytorch", "tensorflow", "airflow", "sql", "nosql", "microservices", "agile", "scrum"
}


class CandidateEvidence(BaseModel):
    id: str = Field(..., description="Stable deterministic evidence ID")
    category: str = Field(..., description="company | position | date | highlight | metric | technology")
    value: str = Field(..., description="Raw text value")
    normalizedValue: str = Field(..., description="Lowercased / stripped value for matching")
    sourcePath: str = Field(..., description="JSON or dotted path in document")
    sectionId: Optional[str] = None
    entryId: Optional[str] = None


class EvidenceStore(BaseModel):
    items: List[CandidateEvidence] = Field(default_factory=list)
    _by_id: Dict[str, CandidateEvidence] = {}
    _by_category: Dict[str, List[CandidateEvidence]] = {}

    def model_post_init(self, __context: Any) -> None:
        self._by_id = {item.id: item for item in self.items}
        self._by_category = {}
        for item in self.items:
            self._by_category.setdefault(item.category, []).append(item)

    def get_by_id(self, evidence_id: str) -> Optional[CandidateEvidence]:
        return self._by_id.get(evidence_id)

    def get_by_category(self, category: str) -> List[CandidateEvidence]:
        return self._by_category.get(category, [])

    def get_all_metrics(self) -> Set[str]:
        return {item.normalizedValue for item in self.get_by_category("metric")}

    def get_all_technologies(self) -> Set[str]:
        return {item.normalizedValue for item in self.get_by_category("technology")}

    def get_all_companies(self) -> Set[str]:
        return {item.normalizedValue for item in self.get_by_category("company")}

    def get_all_positions(self) -> Set[str]:
        return {item.normalizedValue for item in self.get_by_category("position")}

    def get_all_dates(self) -> Set[str]:
        return {item.value for item in self.get_by_category("date")}


def extract_candidate_evidence(document: Dict[str, Any]) -> EvidenceStore:
    """
    Extracts all authoritative candidate evidence from a RenderCV document.
    """
    target = document.get("document", document)
    cv = target.get("cv", {})
    sections = cv.get("sections", [])

    items: List[CandidateEvidence] = []
    seen_ids: Set[str] = set()

    def add_evidence(cat: str, val: str, path: str, sec_id: Optional[str] = None, ent_id: Optional[str] = None, suffix: str = ""):
        if not val or not str(val).strip():
            return
        val_str = str(val).strip()
        norm_val = val_str.lower()

        # Deterministic ID based on path + category + suffix
        id_source = f"{path}:{cat}:{suffix}:{val_str}"
        id_hash = hashlib.sha256(id_source.encode("utf-8")).hexdigest()[:10]
        ev_id = f"ev-{cat[:3]}-{id_hash}"

        if ev_id in seen_ids:
            return
        seen_ids.add(ev_id)

        items.append(
            CandidateEvidence(
                id=ev_id,
                category=cat,
                value=val_str,
                normalizedValue=norm_val,
                sourcePath=path,
                sectionId=sec_id,
                entryId=ent_id,
            )
        )

    for s_idx, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        sec_id = section.get("id", f"sec-{s_idx}")
        sec_type = section.get("entryType", "")
        sec_path = f"cv.sections[{s_idx}]"

        for e_idx, entry in enumerate(section.get("entries", []) or []):
            if not isinstance(entry, dict):
                continue
            ent_id = entry.get("id", f"ent-{e_idx}")
            ent_path = f"{sec_path}.entries[{e_idx}]"

            # Company / Organization / Institution
            company = entry.get("company") or entry.get("institution") or entry.get("name")
            if company:
                add_evidence("company", company, f"{ent_path}.company", sec_id, ent_id)

            # Position / Title / Degree
            position = entry.get("position") or entry.get("title") or entry.get("degree")
            if position:
                add_evidence("position", position, f"{ent_path}.position", sec_id, ent_id)

            # Dates
            start_date = entry.get("start_date")
            end_date = entry.get("end_date") or entry.get("date")
            if start_date or end_date:
                date_str = f"{start_date or ''} - {end_date or 'Present'}"
                add_evidence("date", date_str, f"{ent_path}.dates", sec_id, ent_id)

            # Highlights
            highlights = entry.get("highlights", []) or []
            for h_idx, hl in enumerate(highlights):
                if not isinstance(hl, str):
                    continue
                hl_path = f"{ent_path}.highlights[{h_idx}]"
                add_evidence("highlight", hl, hl_path, sec_id, ent_id, suffix=str(h_idx))

                # Extract metrics from highlight
                for m_match in METRIC_REGEX.finditer(hl):
                    m_val = m_match.group(0).strip()
                    if m_val:
                        add_evidence("metric", m_val, hl_path, sec_id, ent_id, suffix=m_val)

                # Extract technologies from highlight
                hl_words = re.findall(r"[A-Za-z0-9#+.]+", hl.lower())
                for word in hl_words:
                    if word in COMMON_TECH_TOKENS:
                        add_evidence("technology", word, hl_path, sec_id, ent_id, suffix=word)

    return EvidenceStore(items=items)
