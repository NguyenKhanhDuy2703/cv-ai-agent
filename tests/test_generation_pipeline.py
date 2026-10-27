import pytest

from tests.providers import FakeProvider, make_pipeline
from src.llm import LLMTimeoutError
from src.llm.operations import GenerationStepError
from src.schemas.generation import GeneratedSummary
from src.pipeline.generation import CvGenerationPipeline
from src.pipeline.generation.evidence import build_candidate_evidence
from src.pipeline.generation.gaps import detect_gaps
from src.schemas.canonical_validator import validate_canonical_document
from src.schemas.generation import GenerateCvRequest
from tests.helpers import request_payload



class FailingRetriever:
    async def retrieve(self, request, *, top_k=5):
        raise RuntimeError("retriever unavailable")



@pytest.mark.asyncio
async def test_complete_profile_generates_valid_canonical_document_with_stable_ids():
    request = GenerateCvRequest.model_validate(request_payload())
    pipeline = make_pipeline()
    first = await pipeline.generate(request)
    second = await pipeline.generate(request)

    assert first.status in {"success", "partial"}
    assert first.document is not None
    assert validate_canonical_document(first.document)[0] is True
    assert first.cv_yaml.startswith("cv:")
    assert first.document["cv"]["sections"] == second.document["cv"]["sections"]


@pytest.mark.asyncio
async def test_required_gaps_return_needs_input_without_generation():
    payload = request_payload(jobDescription="")
    payload["profile"]["name"] = ""
    payload["profile"]["experiences"] = []
    request = GenerateCvRequest.model_validate(payload)
    result = await make_pipeline().generate(request)

    assert result.status == "needs_input"
    assert result.document is None
    assert {gap.code for gap in result.gaps} >= {
        "missing_job_description", "missing_name", "missing_candidate_evidence",
    }


def test_student_profile_with_complete_education_meets_evidence_minimum():
    payload = request_payload()
    payload["profile"]["experiences"] = []
    payload["profile"]["education"] = [{
        "id": "edu-1", "institution": "Example University", "degree": "BSc", "area": "Computer Science",
    }]
    gaps = detect_gaps(GenerateCvRequest.model_validate(payload))
    assert "missing_candidate_evidence" not in {gap.code for gap in gaps}


def test_whitespace_facts_do_not_meet_evidence_minimum():
    payload = request_payload()
    payload["profile"]["experiences"][0]["facts"] = [" ", ""]
    gaps = detect_gaps(GenerateCvRequest.model_validate(payload))
    assert "missing_candidate_evidence" in {gap.code for gap in gaps}


def test_jd_text_never_enters_candidate_evidence():
    request = GenerateCvRequest.model_validate(request_payload())
    store = build_candidate_evidence(request.profile)
    values = " ".join(item.value for item in store.items)
    assert "PostgreSQL" not in values


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("jobDescription", "missing_job_description"),
        ("name", "missing_name"),
        ("email", "missing_email"),
        ("targetPosition", "missing_target_position"),
    ],
)
def test_each_required_field_has_a_specific_gap(path, expected):
    payload = request_payload()
    if path == "jobDescription":
        payload[path] = ""
    else:
        payload["profile"][path] = ""
    gaps = detect_gaps(GenerateCvRequest.model_validate(payload))
    assert expected in {gap.code for gap in gaps}


def test_phone_location_metrics_and_dates_are_recommended_and_skippable():
    payload = request_payload()
    payload["profile"]["phone"] = ""
    payload["profile"]["location"] = ""
    payload["profile"]["experiences"][0]["facts"] = ["Built reliable Python APIs"]
    payload["profile"]["experiences"][0]["startDate"] = ""
    payload["profile"]["experiences"][0]["endDate"] = ""
    gaps = detect_gaps(GenerateCvRequest.model_validate(payload))
    optional = {"missing_phone", "missing_location", "missing_metrics", "missing_dates"}
    optional_gaps = [gap for gap in gaps if gap.code in optional]
    assert {gap.code for gap in optional_gaps} == optional
    assert all(gap.severity == "recommended" for gap in optional_gaps)


@pytest.mark.asyncio
async def test_corrected_input_creates_a_new_generation():
    first_payload = request_payload()
    first_payload["profile"]["targetPosition"] = ""
    first = await make_pipeline().generate(GenerateCvRequest.model_validate(first_payload))
    assert first.status == "needs_input"

    resumed = await make_pipeline().generate(GenerateCvRequest.model_validate(request_payload(generationId="generation-2")))
    repeated = await make_pipeline().generate(GenerateCvRequest.model_validate(request_payload(generationId="generation-2")))
    assert resumed.document["cv"]["sections"] == repeated.document["cv"]["sections"]


@pytest.mark.asyncio
async def test_writer_failure_is_classified_and_does_not_return_a_fake_cv():
    provider = FakeProvider(errors={GeneratedSummary: LLMTimeoutError("private provider detail")})
    with pytest.raises(GenerationStepError) as failure:
        await CvGenerationPipeline(provider=provider).generate(GenerateCvRequest.model_validate(request_payload()))
    assert failure.value.stage == "summary"
    assert failure.value.code == "LLM_TIMEOUT"
    assert "private provider detail" not in str(failure.value)


@pytest.mark.asyncio
async def test_rag_failure_uses_null_retriever_and_returns_partial():
    result = await make_pipeline(retriever=FailingRetriever()).generate(
        GenerateCvRequest.model_validate(request_payload()),
    )
    assert result.status == "partial"
    assert any("without RAG" in warning for warning in result.report.warnings)
