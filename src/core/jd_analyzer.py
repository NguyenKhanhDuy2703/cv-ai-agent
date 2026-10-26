"""
Structured Job Description (JD) Analyzer.

Extracts:
- Role family and seniority level
- Required and preferred technical skills
- Core responsibilities
- High-priority matching keywords
- Supporting verbatim JD excerpts
"""
import logging
import re
from typing import List, Optional
from pydantic import BaseModel, Field

from ..llm import LLMProvider

logger = logging.getLogger(__name__)


class JDAnalysisOutput(BaseModel):
    role_family: str = Field(..., description="Role family (e.g. Backend Engineering, DevOps/SRE, Frontend)")
    seniority: str = Field(..., description="Seniority level (e.g. Intern, Junior, Mid, Senior, Lead, Principal)")
    required_skills: List[str] = Field(default_factory=list, description="Must-have technical and domain skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have or bonus skills")
    responsibilities: List[str] = Field(default_factory=list, description="Key duties and responsibilities")
    keywords: List[str] = Field(default_factory=list, description="Target ATS / matching keywords")
    supporting_jd_excerpts: List[str] = Field(default_factory=list, description="Direct supporting quotes from the JD")


_JD_SYSTEM_PROMPT = """You are an expert IT Job Description Analyzer.
Analyze the provided Job Description (JD) text and output structured JSON strictly conforming to the requested schema.
- Extract clear, concrete skills (e.g. 'Kubernetes', 'PostgreSQL', 'Go', 'Distributed Systems').
- Identify seniority: 'Junior', 'Mid', 'Senior', 'Lead', 'Principal'.
- Keep supporting excerpts verbatim from the input text.
- Do NOT hallucinate skills not mentioned or strongly implied by the JD.
"""


def fallback_rule_based_jd_analysis(jd_text: str) -> JDAnalysisOutput:
    """Heuristic rule-based analyzer when LLM is offline or in mock test mode."""
    lower = jd_text.lower()

    # Seniority heuristic
    seniority = "Mid"
    if any(k in lower for k in ["lead", "architect", "principal", "head of", "director"]):
        seniority = "Lead"
    elif any(k in lower for k in ["senior", "sr.", "5+ years", "7+ years"]):
        seniority = "Senior"
    elif any(k in lower for k in ["junior", "jr.", "fresher", "intern", "entry"]):
        seniority = "Junior"

    # Role family heuristic
    role = "Software Engineering"
    if any(k in lower for k in ["devops", "sre", "cloud", "infrastructure", "kubernetes"]):
        role = "DevOps / Infrastructure"
    elif any(k in lower for k in ["frontend", "react", "vue", "angular", "ui/ux", "web"]):
        role = "Frontend Engineering"
    elif any(k in lower for k in ["backend", "api", "database", "microservice", "golang", "java", "python"]):
        role = "Backend Engineering"
    elif any(k in lower for k in ["data", "etl", "machine learning", "ai", "spark", "pipeline"]):
        role = "Data / AI Engineering"

    # Keyword extraction
    known_skills = [
        "python", "golang", "java", "typescript", "javascript", "react", "vue",
        "kubernetes", "docker", "aws", "gcp", "azure", "postgresql", "mysql",
        "redis", "kafka", "graphql", "rest", "ci/cd", "terraform", "microservices"
    ]
    extracted = [s for s in known_skills if s in lower]
    req_skills = extracted[:6] if extracted else ["Software Development"]
    pref_skills = extracted[6:10] if len(extracted) > 6 else []

    # Excerpts (first 2-3 non-empty lines)
    lines = [line.strip() for line in jd_text.splitlines() if len(line.strip()) > 15]
    excerpts = lines[:3]

    return JDAnalysisOutput(
        role_family=role,
        seniority=seniority,
        required_skills=req_skills,
        preferred_skills=pref_skills,
        responsibilities=[line for line in lines[1:4]] or ["Build scalable software systems"],
        keywords=extracted,
        supporting_jd_excerpts=excerpts,
    )


class JDAnalyzer:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    async def analyze(self, jd_text: str, language: str = "vi") -> JDAnalysisOutput:
        if not jd_text or not jd_text.strip():
            return JDAnalysisOutput(
                role_family="General IT",
                seniority="Mid",
                required_skills=[],
                preferred_skills=[],
                responsibilities=[],
                keywords=[],
                supporting_jd_excerpts=[],
            )

        if self.provider is None:
            return fallback_rule_based_jd_analysis(jd_text)

        messages = [
            {"role": "system", "content": _JD_SYSTEM_PROMPT},
            {"role": "user", "content": f"Language: {language}\n\nJob Description:\n{jd_text}"},
        ]

        try:
            return await self.provider.generate_structured(JDAnalysisOutput, messages)
        except Exception as exc:
            logger.warning("LLM JD analysis failed, falling back to rule-based: %s", exc)
            return fallback_rule_based_jd_analysis(jd_text)
