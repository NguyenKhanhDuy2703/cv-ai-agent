"""Candidate evidence models and shared matching tokens for generation and guards."""
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
