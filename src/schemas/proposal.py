from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from ..constants.generation import DEFAULT_LANGUAGE


class ControlConfig(BaseModel):
    """CLI source-file parsing options retained for backward-compatible fixtures."""

    locale: Literal["vi", "en"] = Field(default=DEFAULT_LANGUAGE)
    industry: Optional[str] = None
    locked: List[str] = Field(default_factory=list)


class BonusNote(BaseModel):
    attach_to: Optional[str] = None
    text: str


BonusItem = BonusNote


class BonusInput(BaseModel):
    """Additional candidate-supplied notes accepted by the offline source parser."""

    notes: List[BonusNote] = Field(default_factory=list)
    directives: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)
