"""JD analysis uses explicit providers and exposes classified failures."""
import pytest

from src.core.jd_analyzer import JDAnalyzer, JDAnalysisOutput
from src.llm import LLMAuthenticationError
from src.llm.operations import GenerationStepError
from tests.providers import FakeProvider


@pytest.mark.asyncio
async def test_jd_provider_failure_is_not_hidden_by_rule_based_analysis():
    provider = FakeProvider(errors={JDAnalysisOutput: LLMAuthenticationError("invalid private-key")})
    with pytest.raises(GenerationStepError) as failure:
        await JDAnalyzer(provider).analyze("Senior DevOps Engineer with Kubernetes and AWS")
    assert failure.value.code == "LLM_AUTHENTICATION_ERROR"
    assert failure.value.stage == "jd_analysis"
    assert "private-key" not in str(failure.value)


@pytest.mark.asyncio
async def test_jd_analyzer_with_injected_provider():
    provider = FakeProvider()
    expected = JDAnalysisOutput(
        role_family="Backend Engineering", seniority="Senior",
        required_skills=["Python", "FastAPI", "PostgreSQL"], preferred_skills=["Redis"],
        responsibilities=["Build high-throughput APIs"], keywords=["Python", "FastAPI", "PostgreSQL"],
        supporting_jd_excerpts=["Build high-throughput APIs"],
    )
    provider.set_response(JDAnalysisOutput, expected)
    out = await JDAnalyzer(provider).analyze("Senior Backend Engineer with Python and FastAPI")
    assert out == expected


def test_no_implicit_offline_provider():
    with pytest.raises(ValueError, match="explicit LLM provider"):
        JDAnalyzer(None)
