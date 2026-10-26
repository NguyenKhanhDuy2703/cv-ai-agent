"""
CV Input Schema — the legacy source-file shape supported by CLI parse/validate.

This schema covers the information every CV should have.
The frontend UI collects these fields through its own wizard/form flow,
then serialises the result as YAML or JSON to POST to the agent.

Fields:
  - Core CV data (required): name, position, objective, experience, education
  - Optional CV sections: projects, achievements, interests
  - AI-only inputs (not printed in the CV): bonus notes, directives, references
  - Job target: jd (job description text)
  - Run control: locale, locked sections
"""
from typing import Annotated, Optional
from pydantic import BaseModel, Field, field_validator
from .proposal import BonusInput, ControlConfig


class Experience(BaseModel):
    """One work experience entry."""
    company: str = Field(..., description="Company or organisation name")
    title: str = Field(..., description="Job title / role")
    start: str = Field(..., description="Start date, e.g. '2021-01' or '2021'")
    end: Optional[str] = Field(default=None, description="End date; None means current / present")
    location: Optional[str] = Field(default=None)
    highlights: Annotated[list[str], Field(min_length=1)] = Field(
        ..., description="Bullet points describing responsibilities and achievements"
    )


class Project(BaseModel):
    """One project entry (personal, academic, or professional)."""
    name: str
    url: Optional[str] = None
    tech: list[str] = Field(default_factory=list, description="Technologies / tools used")
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """One education entry."""
    institution: str = Field(..., description="University, school, or training centre")
    degree: str = Field(..., description="Degree, diploma, or certificate name")
    year: Optional[str] = Field(default=None, description="Graduation year or date range")
    gpa: Optional[str] = Field(default=None)


class CvInput(BaseModel):
    """
    Top-level source-file schema used by CLI parse/validate.

    The frontend UI collects these fields through its wizard flow and
    serializes them as YAML or JSON for offline source validation.
    """

    # ── Required core fields ─────────────────────────────────────────────────
    name: str = Field(..., description="Full name")
    position: str = Field(..., description="Target job title / position being applied for")
    objective: str = Field(..., description="Career objective or professional summary")

    experience: Annotated[list[Experience], Field(min_length=1)] = Field(
        ..., description="Work experience entries, most recent first. At least one required."
    )
    education: Annotated[list[Education], Field(min_length=1)] = Field(
        ..., description="Education entries. At least one required."
    )

    # ── Optional CV sections ─────────────────────────────────────────────────
    projects: list[Project] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list, description="Awards, certifications, honours")
    interests: list[str] = Field(default_factory=list, description="Hobbies or areas of interest")

    # ── AI-only inputs (not printed in the output CV) ────────────────────────
    bonus: Optional[BonusInput] = Field(
        default=None,
        description="Extra context for the AI: notes, directives, references. Never printed in the CV.",
    )
    jd: Optional[str] = Field(
        default=None,
        description="Job description of the company / role being applied for.",
    )

    # ── Run control ──────────────────────────────────────────────────────────
    control: ControlConfig = Field(default_factory=ControlConfig)

    @field_validator("name", "position", "objective", mode="before")
    @classmethod
    def _strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v
