"""JD analysis behavior with deterministic and mock providers."""

import pytest

from src.core.jd_analyzer import JDAnalyzer, JDAnalysisOutput, fallback_rule_based_jd_analysis
from src.llm.mock_provider import MockProvider


def test_jd_analyzer_fallback():
    jd = """
    Senior DevOps Engineer needed.
    Requirements:
    - 5+ years experience with Kubernetes and AWS
    - Strong skills in Docker, Terraform, CI/CD pipelines
    - Experience in Python or Go scripting
    """
    res = fallback_rule_based_jd_analysis(jd)
    assert res.seniority == "Senior"
    assert "DevOps" in res.role_family
    assert any("kubernetes" in k for k in res.keywords)
    assert any("aws" in k for k in res.keywords)


@pytest.mark.asyncio
async def test_jd_analyzer_with_mock_provider():
    mock_p = MockProvider()
    expected = JDAnalysisOutput(
        role_family="Backend Engineering",
        seniority="Senior",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Redis"],
        responsibilities=["Build high-throughput APIs"],
        keywords=["Python", "FastAPI", "PostgreSQL"],
        supporting_jd_excerpts=["Build high-throughput APIs"],
    )
    mock_p.set_response(JDAnalysisOutput, expected)

    analyzer = JDAnalyzer(provider=mock_p)
    out = await analyzer.analyze("Senior Backend Engineer with Python and FastAPI")
    assert out.role_family == "Backend Engineering"
    assert out.seniority == "Senior"
    assert "Python" in out.required_skills
