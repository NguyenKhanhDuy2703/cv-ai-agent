import pytest
from src.core.evidence_extractor import CandidateEvidence, EvidenceStore
from src.guard.deterministic_guard import DeterministicGuard
from src.core.experience_writer import ExperienceWriter, ProposedBullet, ExperienceRewriteProposals
from src.core.jd_analyzer import JDAnalysisOutput
from src.llm.mock_provider import MockProvider


@pytest.fixture
def sample_evidence_store():
    items = [
        CandidateEvidence(
            id="ev-hl-1",
            category="highlight",
            value="Maintained 30+ Kubernetes clusters with 99.9% uptime",
            normalizedValue="maintained 30+ kubernetes clusters with 99.9% uptime",
            sourcePath="cv.sections[0].entries[0].highlights[0]",
            entryId="ent-1",
        ),
        CandidateEvidence(
            id="ev-met-1",
            category="metric",
            value="30+",
            normalizedValue="30+",
            sourcePath="cv.sections[0].entries[0].highlights[0]",
            entryId="ent-1",
        ),
        CandidateEvidence(
            id="ev-met-2",
            category="metric",
            value="99.9%",
            normalizedValue="99.9%",
            sourcePath="cv.sections[0].entries[0].highlights[0]",
            entryId="ent-1",
        ),
        CandidateEvidence(
            id="ev-tech-1",
            category="technology",
            value="kubernetes",
            normalizedValue="kubernetes",
            sourcePath="cv.sections[0].entries[0].highlights[0]",
            entryId="ent-1",
        ),
    ]
    return EvidenceStore(items=items)


@pytest.mark.parametrize(
    ("proposed", "expected"),
    [
        ("Đã phụ trách dự án 12 tầng và tiết kiệm 25% ngân sách.", True),
        ("Quản lý 30 tầng và tiết kiệm 50% chi phí cho công ty.", False),
    ],
)
def test_vietnamese_metrics_use_the_production_guard(proposed, expected):
    original = "Phụ trách dự án chung cư 12 tầng, tối ưu chi phí 25% cho công ty."
    store = EvidenceStore(items=[CandidateEvidence(
        id="ev-vi-fact", category="highlight", value=original,
        normalizedValue=original.lower(), sourcePath="profile.experiences[0].facts[0]",
    )])
    result = DeterministicGuard.verify(proposed, ["ev-vi-fact"], original, store, "vi")
    assert result.is_valid is expected


def test_guard_valid_proposal_passes(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    proposed = "Orchestrated 30+ production Kubernetes clusters maintaining 99.9% system availability"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1", "ev-met-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is True
    assert len(res.rejection_reasons) == 0


def test_guard_fabricated_metric_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Fabricate 500+ clusters and 99.999% uptime
    proposed = "Managed 500+ clusters achieving 99.999% uptime across global data centers"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is False
    assert any("Numeric fabrication" in r for r in res.rejection_reasons)


def test_guard_missing_evidence_ids_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    proposed = "Orchestrated 30+ production Kubernetes clusters maintaining 99.9% system availability"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=[],  # Missing!
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is False
    assert any("Missing evidenceIds" in r for r in res.rejection_reasons)


def test_guard_invalid_evidence_id_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    proposed = "Orchestrated 30+ production Kubernetes clusters maintaining 99.9% system availability"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-non-existent-id"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is False
    assert any("Invalid evidence IDs" in r for r in res.rejection_reasons)


def test_guard_banned_buzzword_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    proposed = "Rockstar engineer who maintained 30+ Kubernetes clusters with 99.9% uptime"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is False
    assert any("banned buzzword" in r for r in res.rejection_reasons)


def test_guard_too_short_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    proposed = "Short bullet"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
    )
    assert res.is_valid is False
    assert any("too short" in r for r in res.rejection_reasons)


@pytest.mark.asyncio
async def test_experience_writer_with_mock_provider(sample_evidence_store):
    mock_p = MockProvider()
    expected = ExperienceRewriteProposals(
        proposals=[
            ProposedBullet(
                index=0,
                text="Automated operations for 30+ Kubernetes clusters achieving 99.9% availability",
                evidence_ids=["ev-hl-1", "ev-met-1"],
                knowledge_chunk_ids=[],
                rationale="Emphasized automation and high availability",
            )
        ]
    )
    mock_p.set_response(ExperienceRewriteProposals, expected)

    writer = ExperienceWriter(provider=mock_p)
    entry = {
        "id": "ent-1",
        "company": "Cloud Corp",
        "position": "DevOps Engineer",
        "highlights": ["Maintained 30+ Kubernetes clusters with 99.9% uptime"],
    }
    jd = JDAnalysisOutput(
        role_family="DevOps",
        seniority="Senior",
        required_skills=["Kubernetes"],
        preferred_skills=[],
        responsibilities=["Automate cluster infrastructure"],
        keywords=["Kubernetes"],
        supporting_jd_excerpts=["Automate cluster infrastructure"],
    )

    out = await writer.rewrite_entry(entry, jd, sample_evidence_store, language="en")
    assert len(out.proposals) == 1
    assert out.proposals[0].index == 0
    assert "ev-hl-1" in out.proposals[0].evidence_ids


def test_guard_fabricated_company_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Fabricate company Google
    proposed = "Led cluster scaling at Google maintaining 99.9% uptime across production"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
    )
    assert res.is_valid is False
    assert any("Fabricated company" in r for r in res.rejection_reasons)


def test_guard_fabricated_job_title_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Fabricate title Principal Architect
    proposed = "Promoted to Principal Architect maintaining 30+ Kubernetes clusters with 99.9% uptime"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
    )
    assert res.is_valid is False
    assert any("Fabricated job title" in r for r in res.rejection_reasons)


def test_guard_fabricated_certification_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Fabricate CKA certification
    proposed = "Earned Certified Kubernetes Administrator CKA certification and maintained 30+ clusters"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
    )
    assert res.is_valid is False
    assert any("Fabricated certification" in r for r in res.rejection_reasons)


def test_guard_date_inconsistency_rejected(sample_evidence_store):
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Candidate worked in 2023, but proposal claims 2012-2016 tenure
    proposed = "Maintained 30+ Kubernetes clusters with 99.9% uptime from 2012 to 2016"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
        entry_dates={"start_date": "2023-01", "end_date": "2023-12"},
    )
    assert res.is_valid is False
    assert any("Date inconsistency" in r for r in res.rejection_reasons)


def test_guard_corrupt_nonstandard_date_handled(sample_evidence_store):
    """Reviewer Attack Vector 1: CV with non-standard date format like 'Summer 2021' or '2021-06'."""
    orig = "Maintained 30+ Kubernetes clusters with 99.9% uptime"
    # Valid year within 'Summer 2021' -> 'present'
    proposed_valid = "Maintained 30+ Kubernetes clusters with 99.9% uptime since 2021 across regions"
    res_valid = DeterministicGuard.verify(
        proposed_text=proposed_valid,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
        entry_dates={"start_date": "Summer 2021", "end_date": "present"},
    )
    assert res_valid.is_valid is True

    # Invalid year way before Summer 2021 (e.g. 2014)
    proposed_invalid = "Maintained 30+ Kubernetes clusters with 99.9% uptime in 2014 across regions"
    res_invalid = DeterministicGuard.verify(
        proposed_text=proposed_invalid,
        evidence_ids=["ev-hl-1"],
        original_bullet=orig,
        evidence_store=sample_evidence_store,
        language="en",
        current_entry_id="ent-1",
        entry_dates={"start_date": "Summer 2021", "end_date": "present"},
    )
    assert res_invalid.is_valid is False
    assert any("Date inconsistency" in r for r in res_invalid.rejection_reasons)


def test_guard_cross_entry_evidence_contamination_rejected():
    """Evidence from Company B cannot be cited to justify an accomplishment at Company A."""
    store = EvidenceStore(
        items=[
            CandidateEvidence(
                id="ev-comp-a",
                category="highlight",
                value="Engineered payment gateway",
                normalizedValue="engineered payment gateway",
                sourcePath="cv.sections[0].entries[0].highlights[0]",
                entryId="entry-company-a",
            ),
            CandidateEvidence(
                id="ev-comp-b",
                category="highlight",
                value="Scaled telemetry pipeline",
                normalizedValue="scaled telemetry pipeline",
                sourcePath="cv.sections[0].entries[1].highlights[0]",
                entryId="entry-company-b",
            ),
        ]
    )
    # Proposed bullet for entry-company-a illegally cites ev-comp-b
    proposed = "Engineered resilient payment gateway with telemetry pipeline"
    res = DeterministicGuard.verify(
        proposed_text=proposed,
        evidence_ids=["ev-comp-b"],
        original_bullet="Engineered payment gateway",
        evidence_store=store,
        language="en",
        current_entry_id="entry-company-a",
    )
    assert res.is_valid is False
    assert any("Cross-entry evidence contamination" in r for r in res.rejection_reasons)
