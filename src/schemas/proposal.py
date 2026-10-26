from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ControlConfig(BaseModel):
    jd: Optional[str] = Field(default=None, description="Target job description")
    locale: Literal["vi", "en"] = Field(default="vi", description="Target CV language")
    industry: Optional[str] = Field(default=None, description="Target industry (slot for RAG)")
    locked: List[str] = Field(default_factory=list, description="Sections/fields locked from editing")
    max_bullets: Optional[int] = Field(default=None, description="Max bullet points per entry")
    mode: Optional[str] = Field(default="standard", description="Run mode: standard or interactive")


class BonusNote(BaseModel):
    attach_to: Optional[str] = Field(default=None, description="Path or entry id to attach to, e.g. experience[0]")
    text: str = Field(..., description="Note text content")


BonusItem = BonusNote


class BonusInput(BaseModel):
    notes: List[BonusNote] = Field(default_factory=list, description="Attached or general notes")
    directives: List[str] = Field(default_factory=list, description="User commands / preferences (never in CV content)")
    references: List[str] = Field(default_factory=list, description="URLs or reference documents")


class CoreCvInput(BaseModel):
    """
    Core CV structure loaded from YAML.
    """
    name: str
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    raw_extra: Dict[str, Any] = Field(default_factory=dict)


class ChangeItem(BaseModel):
    target: str = Field(..., description="Field path changed, e.g. experience[0].highlights[1]")
    before: str
    after: str
    source: str = Field(..., description="Bonus note, directive, or JD used as source")


class ConflictItem(BaseModel):
    field: str
    core_value: str
    bonus_value: str
    flag: str = Field(..., description="Conflict description")


class CvReport(BaseModel):
    changes: List[ChangeItem] = Field(default_factory=list)
    used_bonus: List[str] = Field(default_factory=list)
    unused_bonus: List[str] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    missing_jd_keywords: List[str] = Field(default_factory=list)
    match_score: Optional[float] = Field(default=None, description="Score matching JD (0 - 100)")
