"""
Tests for SSE Streaming endpoint POST /v1/ai/tailor/stream.
"""
import json
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from src.api.server import app
from src.llm.mock_provider import MockProvider
from src.schemas.internal import (
    JDProfile,
    ObjectiveRewriteOutput,
    ExperienceRewriteOutput,
    RewriteBullet,
)


@pytest.fixture
def mock_llm():
    provider = MockProvider()
    provider.set_response(
        JDProfile,
        JDProfile(
            keywords=["Kubernetes", "AWS", "DevOps"],
            required_skills=["Kubernetes", "AWS"],
            seniority="Senior",
            summary="DevOps Engineer with cloud infra expertise",
        ),
    )
    provider.set_response(
        ObjectiveRewriteOutput,
        ObjectiveRewriteOutput(
            objective="DevOps specialist with deep expertise in Kubernetes and AWS cloud environments.",
        ),
    )
    provider.set_response(
        ExperienceRewriteOutput,
        ExperienceRewriteOutput(
            highlights=[
                RewriteBullet(
                    text="Maintained 30+ Kubernetes clusters with 99.9% uptime across multi-region AWS infrastructure",
                    source_ids=[],
                )
            ]
        ),
    )
    with patch("src.pipeline.orchestrator.get_llm_provider", return_value=provider):
        yield provider


class TestSSEStream:
    def test_tailor_stream_emits_progress_and_done(self, mock_llm):
        client = TestClient(app)
        payload = {
            "cv_input": {
                "name": "Le Van Stream",
                "position": "DevOps Engineer",
                "objective": "DevOps specialist with Kubernetes and AWS experience.",
                "experience": [
                    {
                        "company": "Cloud Corp",
                        "title": "DevOps Lead",
                        "start": "2021",
                        "highlights": ["Maintained 30+ Kubernetes clusters with 99.9% uptime"],
                    }
                ],
                "education": [
                    {
                        "institution": "Polytechnic Institute",
                        "degree": "B.Eng",
                    }
                ],
            }
        }

        response = client.post("/v1/ai/tailor/stream", json=payload)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        content = response.text
        assert "event: validate" in content or "event: progress" in content
        assert "event: done" in content
        assert "Le Van Stream" in content

