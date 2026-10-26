"""
Comprehensive Evaluation Suite for Knowledge Retrieval & Corpus.

Measures:
- Recall@5 across 20 distinct IT evaluation cases (bilingual vi/en)
- Metadata filtering (industry, section, language)
- Non-factual grounding guarantee: Knowledge chunks never inject fabricated metrics
"""
import pytest
from src.knowledge.retriever_protocol import KnowledgeChunk, RetrievalRequest
from src.knowledge.static_retriever import StaticKnowledgeRetriever
from src.guard.deterministic_guard import DeterministicGuard
from src.core.evidence_extractor import CandidateEvidence, EvidenceStore

# 20 Diverse Retrieval Benchmark Cases
EVAL_CASES = [
    {
        "id": "case-01-devops-cloud-en",
        "req": RetrievalRequest(
            query="Senior DevOps Cloud Engineer with Kubernetes, Terraform and AWS CI/CD pipelines",
            language="en",
            role_family="DevOps / Infrastructure",
            seniority="Senior",
            keywords=["Kubernetes", "AWS", "Terraform", "CI/CD"],
        ),
        "expected": {"it-rule-devops-cloud-en", "it-rule-action-verbs-lead-en"},
    },
    {
        "id": "case-02-lead-microservices-vi",
        "req": RetrievalRequest(
            query="Tuyển Tech Lead kiến trúc phân tán microservices và xử lý tải cao",
            language="vi",
            role_family="Backend Engineering",
            seniority="Lead",
            keywords=["microservices", "kiến trúc phân tán"],
        ),
        "expected": {"it-rule-action-verbs-lead-vi", "it-rule-backend-microservices-vi"},
    },
    {
        "id": "case-03-backend-rest-kafka-en",
        "req": RetrievalRequest(
            query="Backend Developer building event-driven microservices with REST, gRPC and Kafka messaging",
            language="en",
            role_family="Backend Engineering",
            seniority="Mid",
            keywords=["Kafka", "microservices", "gRPC", "REST"],
        ),
        "expected": {"it-rule-backend-microservices-en"},
    },
    {
        "id": "case-04-database-indexing-vi",
        "req": RetrievalRequest(
            query="Tối ưu cơ sở dữ liệu PostgreSQL đánh index query execution plan và Redis caching",
            language="vi",
            role_family="Database / Storage",
            keywords=["cơ sở dữ liệu", "index", "Redis", "query"],
        ),
        "expected": {"it-rule-database-tuning-vi"},
    },
    {
        "id": "case-05-database-tuning-en",
        "req": RetrievalRequest(
            query="Database performance tuning, connection pooling, read replicas and Redis cache layer",
            language="en",
            role_family="Database / Storage",
            keywords=["database", "tuning", "redis", "caching"],
        ),
        "expected": {"it-rule-database-tuning-en"},
    },
    {
        "id": "case-06-security-owasp-en",
        "req": RetrievalRequest(
            query="Application security engineer protecting against OWASP Top 10 with OAuth2, JWT and RBAC",
            language="en",
            role_family="Security",
            keywords=["security", "owasp", "oauth2", "rbac"],
        ),
        "expected": {"it-rule-security-practices-en"},
    },
    {
        "id": "case-07-security-rbac-vi",
        "req": RetrievalRequest(
            query="Chuyên viên bảo mật phần mềm, xác thực OAuth2, token JWT và phân quyền người dùng RBAC",
            language="vi",
            role_family="Security",
            keywords=["bảo mật", "oauth2", "rbac", "jwt"],
        ),
        "expected": {"it-rule-security-practices-vi"},
    },
    {
        "id": "case-08-frontend-react-en",
        "req": RetrievalRequest(
            query="Frontend Engineer optimizing bundle size, lazy loading and Core Web Vitals in React apps",
            language="en",
            role_family="Frontend Engineering",
            keywords=["frontend", "react", "bundle", "web vitals"],
        ),
        "expected": {"it-rule-frontend-performance-en"},
    },
    {
        "id": "case-09-frontend-web-vitals-vi",
        "req": RetrievalRequest(
            query="Lập trình viên Frontend tối ưu hiệu năng web, lazy loading, quản lý state Zustand",
            language="vi",
            role_family="Frontend Engineering",
            keywords=["frontend", "hiệu năng", "lazy loading", "state"],
        ),
        "expected": {"it-rule-frontend-performance-vi"},
    },
    {
        "id": "case-10-testing-qa-en",
        "req": RetrievalRequest(
            query="Software QA Automation Engineer writing automated unit test, integration test and SonarQube",
            language="en",
            role_family="Quality Assurance",
            keywords=["testing", "qa", "unit test", "sonarqube"],
        ),
        "expected": {"it-rule-testing-quality-en"},
    },
    {
        "id": "case-11-testing-qa-vi",
        "req": RetrievalRequest(
            query="Kỹ sư kiểm thử chất lượng mã nguồn, tự động hóa unit test, integration test",
            language="vi",
            role_family="Quality Assurance",
            keywords=["kiểm thử", "unit test", "chất lượng"],
        ),
        "expected": {"it-rule-testing-quality-vi"},
    },
    {
        "id": "case-12-data-spark-en",
        "req": RetrievalRequest(
            query="Data Engineer building streaming data pipelines with Apache Spark, Kafka and model serving",
            language="en",
            role_family="Data / AI Engineering",
            keywords=["data", "spark", "kafka", "pipeline"],
        ),
        "expected": {"it-rule-data-ml-pipelines-en"},
    },
    {
        "id": "case-13-data-pipeline-vi",
        "req": RetrievalRequest(
            query="Kỹ sư dữ liệu xây dựng luồng pipeline xử lý dữ liệu lớn Spark và Kafka",
            language="vi",
            role_family="Data / AI Engineering",
            keywords=["dữ liệu", "pipeline", "spark", "kafka"],
        ),
        "expected": {"it-rule-data-ml-pipelines-vi"},
    },
    {
        "id": "case-14-xyz-formula-en",
        "req": RetrievalRequest(
            query="How to structure strong CV achievement bullets using the XYZ impact formula",
            language="en",
            keywords=["xyz formula", "impact", "bullet"],
        ),
        "expected": {"it-rule-xyz-formula-en"},
    },
    {
        "id": "case-15-xyz-formula-vi",
        "req": RetrievalRequest(
            query="Công thức XYZ viết kinh nghiệm làm việc và tác động kỹ thuật trong CV",
            language="vi",
            keywords=["công thức xyz", "tác động"],
        ),
        "expected": {"it-rule-xyz-formula-vi"},
    },
    {
        "id": "case-16-action-verbs-mid-en",
        "req": RetrievalRequest(
            query="Action verbs for mid software developers implementing and maintaining systems",
            language="en",
            seniority="Mid",
            keywords=["action verbs", "developer", "implemented"],
        ),
        "expected": {"it-rule-action-verbs-mid-en"},
    },
    {
        "id": "case-17-action-verbs-mid-vi",
        "req": RetrievalRequest(
            query="Động từ hành động cho lập trình viên phát triển và xây dựng phần mềm",
            language="vi",
            seniority="Mid",
            keywords=["động từ hành động", "phát triển"],
        ),
        "expected": {"it-rule-action-verbs-mid-vi"},
    },
    {
        "id": "case-18-ban-cliches-en",
        "req": RetrievalRequest(
            query="Avoid empty clichés, buzzwords like rockstar, guru or hard-working in resume",
            language="en",
            keywords=["clichés", "buzzwords", "rockstar", "guru"],
        ),
        "expected": {"it-rule-avoid-cliches-en"},
    },
    {
        "id": "case-19-ban-cliches-vi",
        "req": RetrievalRequest(
            query="Tránh các từ sáo rỗng tự khen như chăm chỉ nhiệt huyết trong CV",
            language="vi",
            keywords=["từ sáo rỗng", "chăm chỉ", "tự khen"],
        ),
        "expected": {"it-rule-avoid-cliches-vi"},
    },
    {
        "id": "case-20-concise-length-en",
        "req": RetrievalRequest(
            query="Recommended bullet length, conciseness and line count for software engineer",
            language="en",
            keywords=["concise", "length", "lines", "readability"],
        ),
        "expected": {"it-rule-concise-length-en"},
    },
]


@pytest.mark.asyncio
async def test_retrieval_recall_at_5():
    retriever = StaticKnowledgeRetriever()

    hits = 0
    total = len(EVAL_CASES)

    for case in EVAL_CASES:
        res = await retriever.retrieve(case["req"], top_k=5)
        retrieved_ids = {c.id for c in res.chunks}
        matched = retrieved_ids & case["expected"]
        if matched:
            hits += 1
        else:
            print(f"FAILED CASE {case['id']}: expected {case['expected']}, got {retrieved_ids}")

    recall_at_5 = (hits / total) * 100.0
    print(f"\nEvaluation Results: Recall@5 = {recall_at_5:.1f}% ({hits}/{total})")

    # Acceptance threshold from specification: Recall@5 >= 85%
    assert recall_at_5 >= 85.0, f"Recall@5 is {recall_at_5}%, below threshold 85%"


@pytest.mark.asyncio
async def test_language_isolation():
    retriever = StaticKnowledgeRetriever()

    vi_req = RetrievalRequest(query="Kiến trúc backend", language="vi")
    vi_res = await retriever.retrieve(vi_req, top_k=5)
    for chunk in vi_res.chunks:
        assert chunk.language in ("vi", "all")

    en_req = RetrievalRequest(query="Cloud devops", language="en")
    en_res = await retriever.retrieve(en_req, top_k=5)
    for chunk in en_res.chunks:
        assert chunk.language in ("en", "all")


@pytest.mark.asyncio
async def test_retrieval_filters_industry_section_and_language():
    relevant = KnowledgeChunk(
        id="relevant", title="Cloud writing guidance", content="Cloud deployment guidance",
        industry="it_software", section="experience", language="en",
    )
    chunks = [
        relevant,
        relevant.model_copy(update={"id": "other-industry", "industry": "architecture_construction"}),
        relevant.model_copy(update={"id": "other-section", "section": "projects"}),
        relevant.model_copy(update={"id": "other-language", "language": "vi"}),
    ]
    result = await StaticKnowledgeRetriever(chunks=chunks).retrieve(RetrievalRequest(
        query="Cloud deployment", industry="it_software", section="experience", language="en",
    ))
    assert [chunk.id for chunk in result.chunks] == ["relevant"]


def test_rag_guidance_does_not_permit_hallucination():
    """
    RAG guidance mentions '99.99% uptime' as an illustrative template.
    Guard MUST still reject it if candidate did not have 99.99% in evidence!
    """
    evidence_store = EvidenceStore(
        items=[
            CandidateEvidence(
                id="ev-1",
                category="highlight",
                value="Maintained internal services",
                normalizedValue="maintained internal services",
                sourcePath="cv.sections[0].entries[0].highlights[0]",
            )
        ]
    )

    # Bullet attempting to claim 99.99% uptime from RAG tip
    copied_from_rag_tip = "Architected internal services achieving 99.99% uptime"
    res = DeterministicGuard.verify(
        proposed_text=copied_from_rag_tip,
        evidence_ids=["ev-1"],
        original_bullet="Maintained internal services",
        evidence_store=evidence_store,
        language="en",
    )

    # Must be strictly rejected despite being present in RAG text!
    assert res.is_valid is False
    assert any("Numeric fabrication" in r for r in res.rejection_reasons)
