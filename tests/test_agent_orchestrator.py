import json
from pathlib import Path
import pytest

from src.schemas.canonical_dto import CanonicalTailorRequest, TailorOptions, compute_bullet_hash
from src.schemas.canonical_validator import validate_canonical_document
from src.pipeline.agent_orchestrator import AgentTailorPipeline
from src.llm.mock_provider import MockProvider
from src.core.jd_analyzer import JDAnalysisOutput
from src.core.experience_writer import ExperienceRewriteProposals, ProposedBullet
from src.core.evidence_extractor import extract_candidate_evidence

FIXTURES_DIR = Path("d:/Projects/Render/packages/cv-contracts/fixtures")


@pytest.fixture
def en_fixture():
    path = FIXTURES_DIR / "en.v1.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["document"]


@pytest.mark.asyncio
async def test_end_to_end_tailor_with_mock_provider(en_fixture):
    # Setup MockProvider
    mock_p = MockProvider()

    # Pre-extract evidence to get real evidence IDs for mock response
    ev_store = extract_candidate_evidence(en_fixture)
    exp_bullet_evs = [
        ev.id for ev in ev_store.items
        if ev.category == "highlight" and ev.entryId == "ent-exp-1"
    ]

    mock_p.set_response(
        JDAnalysisOutput,
        JDAnalysisOutput(
            role_family="Software Engineering",
            seniority="Senior",
            required_skills=["Python", "Distributed Systems"],
            preferred_skills=["Kubernetes"],
            responsibilities=["Scale core backend services"],
            keywords=["Python", "Distributed Systems"],
            supporting_jd_excerpts=["Scale core backend services"],
        ),
    )

    mock_p.set_response(
        ExperienceRewriteProposals,
        ExperienceRewriteProposals(
            proposals=[
                ProposedBullet(
                    index=0,
                    text="Architected high-throughput foundation model infrastructure serving 2M+ monthly API requests with 99.97% uptime",
                    evidence_ids=exp_bullet_evs[:2],
                    knowledge_chunk_ids=[],
                    rationale="Enhanced alignment with infrastructure JD while grounding in candidate evidence",
                )
            ]
        ),
    )

    pipeline = AgentTailorPipeline(provider=mock_p)

    events = []
    async def track_progress(ev):
        events.append(ev)

    request = CanonicalTailorRequest(
        requestId="req-123",
        cvId="cv-456",
        baseVersion=1,
        document=en_fixture,
        jobDescription="Looking for a Senior Python Software Engineer with experience in distributed systems.",
        instruction="Focus on backend and scalability.",
        options=TailorOptions(language="en", industry="it_software"),
    )

    report = await pipeline.tailor_document(request, on_progress=track_progress)

    # Acceptance criteria
    assert report.status in ["success", "partial"]
    assert len(report.acceptedPatches) > 0
    assert report.appliedDocument is not None

    # Validate output document against canonical Render schema
    is_valid, errors = validate_canonical_document(report.appliedDocument)
    assert is_valid is True, f"Output document failed validation: {errors}"

    # Verify event stream sequence
    event_types = [e["type"] for e in events]
    assert "started" in event_types
    assert "input_validated" in event_types
    assert "jd_analyzed" in event_types
    assert "retrieval_completed" in event_types
    assert "completed" in event_types


@pytest.mark.asyncio
async def test_guard_rejects_hallucination_and_preserves_original(en_fixture):
    mock_p = MockProvider()

    mock_p.set_response(
        JDAnalysisOutput,
        JDAnalysisOutput(
            role_family="DevOps",
            seniority="Senior",
            required_skills=["AWS"],
            preferred_skills=[],
            responsibilities=[],
            keywords=["AWS"],
            supporting_jd_excerpts=[],
        ),
    )

    # Return fabricated metric 99.9999% and 1000x
    mock_p.set_response(
        ExperienceRewriteProposals,
        ExperienceRewriteProposals(
            proposals=[
                ProposedBullet(
                    index=0,
                    text="Delivered 1000x faster deployment pipelines with 99.9999% uptime guarantees",
                    evidence_ids=["ev-fake-1"],
                    knowledge_chunk_ids=[],
                    rationale="Fabricated numbers test",
                )
            ]
        ),
    )

    pipeline = AgentTailorPipeline(provider=mock_p)

    request = CanonicalTailorRequest(
        requestId="req-hallucinate-1",
        cvId="cv-456",
        baseVersion=1,
        document=en_fixture,
        jobDescription="Looking for an engineer",
        options=TailorOptions(language="en"),
    )

    report = await pipeline.tailor_document(request)

    # Must be rejected, status degraded or unchanged, original preserved
    assert len(report.acceptedPatches) == 0
    rejected = [p for p in report.proposals if p.status == "rejected"]
    assert len(rejected) > 0
    # Original document preserved intact
    assert report.appliedDocument == en_fixture


@pytest.mark.asyncio
async def test_locking_bullet_0_does_not_lock_subsequent_bullets(en_fixture):
    mock_p = MockProvider()
    ev_store = extract_candidate_evidence(en_fixture)
    exp_bullet_evs = [
        ev.id for ev in ev_store.items
        if ev.category == "highlight" and ev.entryId == "ent-exp-1"
    ]

    mock_p.set_response(
        JDAnalysisOutput,
        JDAnalysisOutput(
            role_family="Infrastructure",
            seniority="Senior",
            required_skills=["Python"],
            preferred_skills=[],
            responsibilities=["Scale infrastructure"],
            keywords=["Python"],
            supporting_jd_excerpts=["Scale infrastructure"],
        ),
    )

    # Propose rewrites for both bullet 0 and bullet 1
    mock_p.set_response(
        ExperienceRewriteProposals,
        ExperienceRewriteProposals(
            proposals=[
                ProposedBullet(
                    index=0,
                    text="Architected foundation model infrastructure serving 2M+ monthly API requests with 99.97% uptime",
                    evidence_ids=exp_bullet_evs[:2],
                    knowledge_chunk_ids=[],
                    rationale="Bullet 0 rewrite",
                ),
                ProposedBullet(
                    index=1,
                    text="Secured $18M Series A investment co-led by Sequoia Capital to accelerate foundational research",
                    evidence_ids=[exp_bullet_evs[1]],
                    knowledge_chunk_ids=[],
                    rationale="Bullet 1 rewrite",
                ),
            ]
        ),
    )

    pipeline = AgentTailorPipeline(provider=mock_p)

    # Explicitly lock ONLY bullet 0 of ent-exp-1
    request = CanonicalTailorRequest(
        requestId="req-lock-0",
        cvId="cv-456",
        baseVersion=1,
        document=en_fixture,
        jobDescription="Looking for an infrastructure engineer",
        options=TailorOptions(
            language="en",
            lockedPaths=["sec-experience.ent-exp-1.highlights[0]"],
        ),
    )

    report = await pipeline.tailor_document(request)

    # Bullet 0 must be unchanged because locked
    b0_report = next(p for p in report.proposals if p.patch.entryId == "ent-exp-1" and p.patch.index == 0)
    assert b0_report.status == "unchanged"
    assert "locked" in b0_report.reason.lower()

    # Bullet 1 MUST be accepted (not accidentally skipped or locked!)
    b1_report = next(p for p in report.proposals if p.patch.entryId == "ent-exp-1" and p.patch.index == 1)
    assert b1_report.status == "accepted"
    assert any(p.entryId == "ent-exp-1" and p.index == 1 for p in report.acceptedPatches)
