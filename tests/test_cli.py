"""
Tests for CV AI Agent CLI (src/cli.py).
"""
from pathlib import Path
import pytest
from src.cli import main
from src.llm.mock_provider import MockProvider
from src.schemas.internal import (
    JDProfile,
    ObjectiveRewriteOutput,
    ExperienceRewriteOutput,
    RewriteBullet,
)
from src.yaml_layer.io import parse_yaml


@pytest.fixture
def mock_cli_llm():
    provider = MockProvider()
    provider.set_response(
        JDProfile,
        JDProfile(
            keywords=["Python", "PostgreSQL", "AWS", "Kubernetes"],
            required_skills=["Python", "Kubernetes"],
            seniority="Senior",
            summary="Senior Backend role focusing on high concurrency",
        ),
    )
    provider.set_response(
        ObjectiveRewriteOutput,
        ObjectiveRewriteOutput(
            objective="Kỹ sư phần mềm 5 năm kinh nghiệm chuyên sâu về Python, kiến trúc microservices và hệ thống phân tán chịu tải lớn.",
        ),
    )
    provider.set_response(
        ExperienceRewriteOutput,
        ExperienceRewriteOutput(
            highlights=[
                RewriteBullet(
                    text="Thiết kế và triển khai cụm microservices xử lý 15.000 requests/s với thời gian phản hồi dưới 50ms",
                    source_ids=[],
                ),
                RewriteBullet(
                    text="Tối ưu hóa cơ sở dữ liệu PostgreSQL và Redis caching giúp giảm 40% chi phí hạ tầng AWS",
                    source_ids=[],
                ),
                RewriteBullet(
                    text="Chủ trì xây dựng pipeline CI/CD tự động hoá kiểm thử và triển khai trên Kubernetes",
                    source_ids=[],
                ),
            ]
        ),
    )
    return provider


def test_cli_validate_yaml():
    exit_code = main(["validate", "-i", "tests/golden/sample_cv_vi.yaml"])
    assert exit_code == 0


def test_cli_validate_markdown():
    exit_code = main(["validate", "-i", "tests/golden/sample_cv_markdown.md"])
    assert exit_code == 0


def test_cli_parse_markdown_to_yaml(tmp_path: Path):
    out_file = tmp_path / "parsed_out.yaml"
    exit_code = main(["parse", "-i", "tests/golden/sample_cv_markdown.md", "-o", str(out_file)])
    assert exit_code == 0
    assert out_file.exists()

    data = parse_yaml(out_file.read_text(encoding="utf-8"))
    assert data["name"] == "Tran Thi Mai"
    assert data["position"] == "Senior BIM Coordinator / Architect"
    assert len(data["experience"]) >= 1


def test_cli_tailor(tmp_path: Path, mock_cli_llm):
    out_yaml = tmp_path / "tailored.yaml"
    out_report = tmp_path / "report.yaml"

    exit_code = main(
        [
            "tailor",
            "-i", "tests/golden/sample_cv_vi.yaml",
            "-j", "tests/golden/sample_jd.txt",
            "-o", str(out_yaml),
            "-r", str(out_report),
            "--locale", "vi",
            "--industry", "it_software",
        ],
        llm_provider=mock_cli_llm,
    )

    assert exit_code == 0
    assert out_yaml.exists()
    assert out_report.exists()

    tailored_data = parse_yaml(out_yaml.read_text(encoding="utf-8"))
    assert tailored_data["name"] == "Nguyễn Văn An"
    assert "experience" in tailored_data

    report_data = parse_yaml(out_report.read_text(encoding="utf-8"))
    assert "changes" in report_data


def test_cli_nonexistent_file():
    exit_code = main(["validate", "-i", "tests/golden/nonexistent_cv.yaml"])
    assert exit_code == 1
