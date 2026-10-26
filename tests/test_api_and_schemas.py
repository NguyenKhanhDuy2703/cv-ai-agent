import pytest
from src.schemas.cv import CvAiData, CvSection, ExperienceEntry
from src.schemas.context import AiRequestContext
from src.guard.anti_hallucination import AntiHallucinationGuard
from src.pipeline.orchestrator import CvTailorPipeline
from src.schemas.proposal import CoreCvInput, BonusInput, BonusNote, ControlConfig


def test_cv_schema_validation():
    cv_data = CvAiData(
        name="Nguyen Van A",
        headline="Senior Architect",
        email="a@example.com",
        sections=[
            CvSection(
                id="sec-1",
                title="Experience",
                entryType="Experience",
                entries=[
                    ExperienceEntry(
                        id="exp-1",
                        company="Vingroup",
                        position="Architect",
                        highlights=["Designed 12-storey residential tower", "Coordinated BIM team"],
                    )
                ],
            )
        ],
    )
    assert cv_data.name == "Nguyen Van A"
    assert len(cv_data.sections[0].entries) == 1
    assert cv_data.sections[0].entries[0].company == "Vingroup"


def test_anti_hallucination_guard():
    source_texts = [
        "Phụ trách dự án chung cư 12 tầng",
        "Tối ưu chi phí 25% cho công ty",
    ]

    # Valid output (all numbers exist in sources)
    valid_bullet = "Đã phụ trách thành công dự án 12 tầng và tiết kiệm 25% ngân sách."
    is_valid, unverified = AntiHallucinationGuard.verify_facts(valid_bullet, source_texts)
    assert is_valid is True
    assert len(unverified) == 0

    # Fabricated metric (e.g. 50% or 30 tầng)
    fabricated_bullet = "Quản lý 30 tầng và tiết kiệm 50% chi phí."
    is_valid, unverified = AntiHallucinationGuard.verify_facts(fabricated_bullet, source_texts)
    assert is_valid is False
    assert "30" in unverified or "50%" in unverified


def test_pipeline_mvp():
    core = CoreCvInput(
        name="Tran Van B",
        headline="Software Engineer",
        email="b@example.com",
    )
    bonus = BonusInput(
        notes=[
            BonusNote(attach_to="experience[0]", text="Dự án 12 tầng"),
            BonusNote(text="Giải nhì thiết kế 2021"),
        ],
        directives=["Nhấn mạnh BIM"],
    )
    control = ControlConfig(locale="vi")
    pipeline = CvTailorPipeline(control)

    out_cv, report = pipeline.run_mvp(core, bonus)
    assert out_cv["name"] == "Tran Van B"
    assert len(report.used_bonus) == 2


def test_api_health_endpoint():
    from fastapi.testclient import TestClient
    from src.api.server import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "live"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"



def test_api_root_redirects_to_docs():
    from fastapi.testclient import TestClient
    from src.api.server import app

    client = TestClient(app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [302, 307]
    assert "/docs" in response.headers["location"]






