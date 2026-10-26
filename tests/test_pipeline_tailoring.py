"""
Unit tests for the end-to-end tailoring pipeline using MockProvider.
Tests STAR rewriting, JD integration, guard enforcement, and YAML output.
"""
import pytest
from src.llm.mock_provider import MockProvider
from src.pipeline.orchestrator import CvTailorPipeline
from src.schemas.cv_input import CvInput, Experience, Education
from src.schemas.internal import (
    JDProfile,
    ExperienceRewriteOutput,
    RewriteBullet,
)
from src.schemas.proposal import BonusInput, BonusNote, ControlConfig
from src.yaml_layer.io import parse_yaml


@pytest.fixture
def sample_cv_input() -> CvInput:
    return CvInput(
        name="Tran Van B",
        position="Senior Backend Engineer",
        objective="5 years of backend engineering experience with microservices and Python.",
        experience=[
            Experience(
                company="TechCorp",
                title="Backend Developer",
                start="2021-01",
                end="2024-01",
                highlights=[
                    "Built microservices handling 10k requests per second",
                    "Optimized PostgreSQL queries reducing latency by 35%",
                ],
            )
        ],
        education=[
            Education(
                institution="Bach Khoa University",
                degree="B.S. Computer Science",
                year="2020",
            )
        ],
        bonus=BonusInput(
            notes=[
                BonusNote(attach_to="experience[0]", text="Led migration to AWS ECS with zero downtime and 99.99% uptime"),
                BonusNote(text="General award: Employee of the year 2022"),
            ],
            directives=[
                "Không nhắc PHP",
                "Nhấn mạnh microservices",
            ],
        ),
        jd="Seeking a Senior Backend Engineer proficient in Python, PostgreSQL, and AWS ECS microservices.",
        control=ControlConfig(locale="vi"),
    )


class TestPipelineTailoring:
    @pytest.mark.asyncio
    async def test_successful_tailor_flow(self, sample_cv_input):
        mock_provider = MockProvider()

        # Mock JDProfile response
        mock_provider.set_response(
            JDProfile,
            JDProfile(
                keywords=["Python", "PostgreSQL", "AWS ECS", "Microservices"],
                required_skills=["Microservices", "Python"],
                seniority="Senior",
                summary="Senior Backend Engineer focusing on scalable systems",
            ),
        )

        # Mock Objective rewrite response
        from src.schemas.internal import ObjectiveRewriteOutput
        mock_provider.set_response(
            ObjectiveRewriteOutput,
            ObjectiveRewriteOutput(
                objective="Chuyên gia Backend với 5 năm kinh nghiệm về microservices và hệ thống phân tán hiệu năng cao.",
            ),
        )

        # Mock Experience rewrite response
        mock_provider.set_response(
            ExperienceRewriteOutput,
            ExperienceRewriteOutput(
                highlights=[
                    RewriteBullet(
                        text="Xây dựng và vận hành hệ thống microservices phục vụ 10k requests/s, đảm bảo uptime 99.99%",
                        source_ids=["frag_0"],
                    ),
                    RewriteBullet(
                        text="Tối ưu hoá các truy vấn PostgreSQL phức tạp, giúp giảm 35% độ trễ hệ thống",
                        source_ids=["frag_0"],
                    ),
                ]
            ),
        )

        progress_events = []
        async def track_progress(event):
            progress_events.append(event)

        pipeline = CvTailorPipeline()
        cv_yaml, report, tailored_cv = await pipeline.tailor(
            sample_cv_input,
            mock_provider,
            on_progress=track_progress,
        )

        # Verify output YAML is valid and parseable
        parsed_doc = parse_yaml(cv_yaml)
        assert parsed_doc["name"] == "Tran Van B"
        assert parsed_doc["position"] == "Senior Backend Engineer"
        # Verify highlights were updated
        assert len(parsed_doc["experience"][0]["highlights"]) == 2
        assert "microservices" in parsed_doc["experience"][0]["highlights"][0].lower()

        # Verify objective was updated
        assert "Chuyên gia Backend" in tailored_cv.objective

        # Verify progress events emitted
        assert len(progress_events) >= 4
        steps_emitted = [e["step"] for e in progress_events]
        assert "validate" in steps_emitted
        assert "jd_analysis" in steps_emitted
        assert "objective" in steps_emitted
        assert "experience" in steps_emitted
        assert "done" in steps_emitted

        # Verify report details
        assert len(report.changes) >= 3  # 1 objective + 2 highlights
        assert report.match_score is not None
        assert report.match_score > 0
        assert len(report.used_bonus) > 0

    @pytest.mark.asyncio
    async def test_guard_rejects_hallucinated_metric_and_keeps_original(self, sample_cv_input):
        mock_provider = MockProvider()

        mock_provider.set_response(
            ExperienceRewriteOutput,
            ExperienceRewriteOutput(
                highlights=[
                    # "500%" is NOT in evidence
                    RewriteBullet(text="Tăng trưởng doanh thu 500% trong năm đầu tiên"),
                    # "35%" IS in evidence
                    RewriteBullet(text="Tối ưu hoá PostgreSQL giảm 35% độ trễ"),
                ]
            ),
        )

        # Remove JD to test direct rewrite mode
        sample_cv_input.jd = None
        pipeline = CvTailorPipeline()
        cv_yaml, report, tailored_cv = await pipeline.tailor(sample_cv_input, mock_provider)

        # First bullet should be kept original due to guard rejection
        exp = tailored_cv.experience[0]
        assert exp.highlights[0] == "Built microservices handling 10k requests per second"
        # Second bullet should be accepted
        assert exp.highlights[1] == "Tối ưu hoá PostgreSQL giảm 35% độ trễ"
        assert len(report.changes) == 1

    @pytest.mark.asyncio
    async def test_locked_experience_is_not_rewritten(self, sample_cv_input):
        mock_provider = MockProvider()
        # Lock experience[0]
        sample_cv_input.control.locked = ["experience[0]"]

        pipeline = CvTailorPipeline()
        cv_yaml, report, tailored_cv = await pipeline.tailor(sample_cv_input, mock_provider)

        # Highlights should remain exactly as input
        assert tailored_cv.experience[0].highlights == [
            "Built microservices handling 10k requests per second",
            "Optimized PostgreSQL queries reducing latency by 35%",
        ]
        assert len(report.changes) == 0
