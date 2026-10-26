import json
from pathlib import Path
import pytest

from src.core.evidence_extractor import extract_candidate_evidence
from src.core.jd_analyzer import JDAnalyzer, JDAnalysisOutput, fallback_rule_based_jd_analysis
from src.llm.mock_provider import MockProvider

FIXTURES_DIR = Path("d:/Projects/Render/packages/cv-contracts/fixtures")


@pytest.fixture
def en_fixture():
    path = FIXTURES_DIR / "en.v1.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["document"]


def test_extract_evidence_from_fixture(en_fixture):
    store = extract_candidate_evidence(en_fixture)
    assert len(store.items) > 0

    # Companies
    companies = store.get_by_category("company")
    assert len(companies) > 0
    assert any("Princeton" in c.value or "Software" in c.value or len(c.value) > 2 for c in companies)

    # Positions
    positions = store.get_by_category("position")
    assert len(positions) > 0

    # Highlights
    highlights = store.get_by_category("highlight")
    assert len(highlights) > 0

    # Deterministic IDs
    for item in store.items:
        assert item.id.startswith("ev-")
        assert len(item.sourcePath) > 0
        assert item.normalizedValue == item.value.strip().lower()


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
