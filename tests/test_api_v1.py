import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.config import settings
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


@pytest.fixture
def mock_pipeline_llm(en_fixture, monkeypatch):
    mock_p = MockProvider()
    ev_store = extract_candidate_evidence(en_fixture)
    hl_evs = [
        ev.id for ev in ev_store.items
        if ev.category == "highlight" and ev.entryId == "ent-exp-1"
    ]

    mock_p.set_response(
        JDAnalysisOutput,
        JDAnalysisOutput(
            role_family="Infrastructure",
            seniority="Senior",
            required_skills=["Kubernetes", "AWS"],
            preferred_skills=[],
            responsibilities=["Scale cloud clusters"],
            keywords=["Kubernetes", "AWS"],
            supporting_jd_excerpts=["Scale cloud clusters"],
        ),
    )

    mock_p.set_response(
        ExperienceRewriteProposals,
        ExperienceRewriteProposals(
            proposals=[
                ProposedBullet(
                    index=0,
                    text="Architected high-throughput foundation model infrastructure serving 2M+ monthly API requests with 99.97% uptime",
                    evidence_ids=hl_evs[:2],
                    knowledge_chunk_ids=[],
                    rationale="Aligned with infrastructure JD",
                )
            ]
        ),
    )

    monkeypatch.setattr("src.pipeline.agent_orchestrator.get_llm_provider", lambda: mock_p)
    return mock_p


def test_sync_tailor_endpoint(en_fixture, mock_pipeline_llm):
    client = TestClient(app)
    payload = {
        "requestId": "req-sync-1",
        "cvId": "cv-test-1",
        "baseVersion": 1,
        "schemaVersion": "1",
        "document": en_fixture,
        "jobDescription": "Senior Cloud Infrastructure Engineer with Kubernetes experience.",
        "instruction": "Highlight high uptime and scale.",
        "options": {
            "language": "en",
            "industry": "it_software",
            "lockedPaths": [],
        },
    }

    res = client.post("/v1/ai/tailor", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["requestId"] == "req-sync-1"
    assert data["status"] in ["success", "partial"]
    assert len(data["acceptedPatches"]) > 0
    assert data["appliedDocument"] is not None


def test_streaming_tailor_endpoint(en_fixture, mock_pipeline_llm):
    client = TestClient(app)
    payload = {
        "requestId": "req-stream-1",
        "cvId": "cv-test-2",
        "baseVersion": 1,
        "schemaVersion": "1",
        "document": en_fixture,
        "jobDescription": "Senior Cloud Infrastructure Engineer with Kubernetes experience.",
        "options": {
            "language": "en",
            "industry": "it_software",
        },
    }

    res = client.post("/v1/ai/tailor/stream", json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    content = res.text
    assert "event: started" in content
    assert "event: completed" in content
    assert '"runId": "req-stream-1"' in content
    assert '"sequence":' in content


def test_service_bearer_auth(en_fixture, mock_pipeline_llm, monkeypatch):
    monkeypatch.setattr(settings, "ai_secret_key", "secret-service-token-123")
    client = TestClient(app)

    payload = {
        "requestId": "req-auth-1",
        "cvId": "cv-test-auth",
        "baseVersion": 1,
        "document": en_fixture,
        "jobDescription": "Test JD",
    }

    # 1. Missing auth header -> 401
    res_no_auth = client.post("/v1/ai/tailor", json=payload)
    assert res_no_auth.status_code == 401

    # 2. Wrong token -> 401
    res_bad_auth = client.post(
        "/v1/ai/tailor",
        json=payload,
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert res_bad_auth.status_code == 401

    # 3. Correct token -> 200
    res_ok = client.post(
        "/v1/ai/tailor",
        json=payload,
        headers={"Authorization": "Bearer secret-service-token-123"},
    )
    assert res_ok.status_code == 200


def test_payload_size_limit():
    client = TestClient(app)
    # Simulate oversized Content-Length header
    headers = {"Content-Length": str(20 * 1024 * 1024)}  # 20MB
    res = client.post("/v1/ai/tailor", data="x", headers=headers)
    assert res.status_code == 413
