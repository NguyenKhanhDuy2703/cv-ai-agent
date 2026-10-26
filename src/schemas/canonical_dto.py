"""
Canonical DTOs for Render CV AI Tailoring and Semantic Patching MVP.
Matches contracts defined between Render Backend and AI Agent.
"""
import hashlib
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


def compute_bullet_hash(text: str) -> str:
    """Computes deterministic SHA256 hex digest for a bullet string."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class TailorOptions(BaseModel):
    language: str = Field(default="vi", description="Language code: vi or en")
    industry: str = Field(default="it_software", description="Target industry code")
    lockedPaths: List[str] = Field(
        default_factory=list,
        description="List of locked JSON/stable paths that must not be altered, e.g. 'sec-1.ent-1' or 'sections[0].entries[0]'",
    )


class CanonicalTailorRequest(BaseModel):
    requestId: str = Field(..., description="Unique request UUID")
    cvId: str = Field(..., description="Target CV UUID")
    baseVersion: int = Field(..., description="Render CV optimistic lock base version number")
    schemaVersion: str = Field(default="1", description="Canonical document schema version")
    document: Dict[str, Any] = Field(..., description="RenderCV canonical document dict")
    jobDescription: str = Field(..., description="Job description text")
    instruction: Optional[str] = Field(default="", description="Optional extra user tailoring instruction")
    options: TailorOptions = Field(default_factory=TailorOptions)


class SemanticPatch(BaseModel):
    op: Literal["replace"] = "replace"
    sectionId: str = Field(..., description="Stable ID of the target section")
    entryId: str = Field(..., description="Stable ID of the target entry")
    field: Literal["highlights"] = "highlights"
    index: int = Field(..., description="Index of the bullet in highlights array")
    beforeHash: str = Field(..., description="SHA256 hex digest of the original bullet before change")
    value: str = Field(..., description="New replacement bullet string")
    evidenceIds: List[str] = Field(default_factory=list, description="IDs of candidate evidence supporting this bullet")
    knowledgeChunkIds: List[str] = Field(default_factory=list, description="IDs of knowledge chunks referenced")


class PatchProposalReport(BaseModel):
    patch: SemanticPatch
    originalValue: str
    status: Literal["accepted", "rejected", "unchanged"] = "accepted"
    reason: Optional[str] = None
    guardChecks: Dict[str, bool] = Field(default_factory=dict)


class TailorDiffReport(BaseModel):
    requestId: str
    cvId: str
    baseVersion: int
    status: Literal["success", "partial", "degraded", "failed"] = "success"
    acceptedPatches: List[SemanticPatch] = Field(default_factory=list)
    proposals: List[PatchProposalReport] = Field(default_factory=list)
    summary: str = ""
    appliedDocument: Optional[Dict[str, Any]] = None
