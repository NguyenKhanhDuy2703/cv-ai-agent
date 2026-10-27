"""
Structured Job Description (JD) Analyzer.

Extracts:
- Role family and seniority level
- Required and preferred technical skills
- Core responsibilities
- High-priority matching keywords
- Supporting verbatim JD excerpts
"""
from typing import List
from pydantic import BaseModel, Field

from ..llm import LLMProvider

from ..llm.operations import generate_at_stage, require_provider


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


class JDAnalyzer:
    def __init__(self, provider: LLMProvider):
        self.provider = require_provider(provider)

    async def analyze(self, jd_text: str, language: str = "vi") -> JDAnalysisOutput:
        if not jd_text.strip():
            raise ValueError("A job description is required")

        messages = [
            {"role": "system", "content": _JD_SYSTEM_PROMPT},
            {"role": "user", "content": f"Language: {language}\n\nJob Description:\n{jd_text}"},
        ]

        return await generate_at_stage(self.provider, JDAnalysisOutput, messages, "jd_analysis")
