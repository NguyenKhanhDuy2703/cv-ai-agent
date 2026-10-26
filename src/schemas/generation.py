"""Contracts for the stateless Generate CV pipeline."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class CandidateExperience(ContractModel):
    id: str = Field(min_length=1)
    company: str = ""
    position: str = ""
    start_date: str = Field(default="", alias="startDate")
    end_date: str = Field(default="", alias="endDate")
    date: str = ""
    location: str = ""
    facts: List[str] = Field(default_factory=list)


class CandidateEducation(ContractModel):
    id: str = Field(min_length=1)
    institution: str = ""
    area: str = ""
    degree: str = ""
    start_date: str = Field(default="", alias="startDate")
    end_date: str = Field(default="", alias="endDate")
    date: str = ""
    location: str = ""
    facts: List[str] = Field(default_factory=list)


class CandidateProject(ContractModel):
    id: str = Field(min_length=1)
    name: str = ""
    url: str = ""
    technologies: List[str] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)


class CandidateListItem(ContractModel):
    id: str = Field(min_length=1)
    name: str = ""
    details: str = ""
    date: str = ""


class CandidateSocialNetwork(ContractModel):
    id: str = Field(min_length=1)
    network: str
    username: str


class CandidateProfile(ContractModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    website: str = ""
    photo_url: str = Field(default="", alias="photoUrl")
    target_position: str = Field(default="", alias="targetPosition")
    social_networks: List[CandidateSocialNetwork] = Field(default_factory=list, alias="socialNetworks")
    experiences: List[CandidateExperience] = Field(default_factory=list)
    education: List[CandidateEducation] = Field(default_factory=list)
    projects: List[CandidateProject] = Field(default_factory=list)
    skills: List[CandidateListItem] = Field(default_factory=list)
    certifications: List[CandidateListItem] = Field(default_factory=list)
    achievements: List[CandidateListItem] = Field(default_factory=list)
    languages: List[CandidateListItem] = Field(default_factory=list)


class GenerateCvOptions(ContractModel):
    language: Literal["vi", "en"] = "vi"
    industry: str = "it_software"
    template_slug: str = Field(default="classic", alias="templateSlug")


class RenderDefaults(ContractModel):
    design: Dict[str, Any]
    locale: Dict[str, Any]
    settings: Dict[str, Any]


class GenerateCvRequest(ContractModel):
    request_id: str = Field(alias="requestId", min_length=1)
    generation_id: str = Field(alias="generationId", min_length=1)
    job_description: str = Field(default="", alias="jobDescription")
    profile: CandidateProfile
    options: GenerateCvOptions = Field(default_factory=GenerateCvOptions)
    render_defaults: RenderDefaults = Field(alias="renderDefaults")


class GenerationGap(ContractModel):
    code: str
    field: str
    severity: Literal["required", "recommended"]
    message: str
    question: Optional[str] = None


class GenerationReport(ContractModel):
    request_id: str = Field(alias="requestId")
    generation_id: str = Field(alias="generationId")
    used_evidence_ids: List[str] = Field(default_factory=list, alias="usedEvidenceIds")
    missing_jd_keywords: List[str] = Field(default_factory=list, alias="missingJdKeywords")
    warnings: List[str] = Field(default_factory=list)


class GenerateCvResult(ContractModel):
    status: Literal["success", "partial", "needs_input", "failed"]
    document: Optional[Dict[str, Any]] = None
    cv_yaml: Optional[str] = Field(default=None, alias="cvYaml")
    report: GenerationReport
    gaps: List[GenerationGap] = Field(default_factory=list)


class GeneratedSummary(ContractModel):
    text: str
    evidence_ids: List[str] = Field(alias="evidenceIds")


class GeneratedProject(ContractModel):
    source_id: str = Field(alias="sourceId")
    highlights: List[str]
    evidence_ids: List[str] = Field(alias="evidenceIds")
