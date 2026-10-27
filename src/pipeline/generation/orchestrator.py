"""Single production orchestrator for generating a new canonical CV."""

from typing import Any, Awaitable, Callable, Dict, List, Optional

from ...constants.generation import PROGRESS_MESSAGES, RAG_TOP_K
from ...core.jd_analyzer import JDAnalyzer
from ...knowledge.null_retriever import NullKnowledgeRetriever
from ...knowledge.retriever_protocol import KnowledgeRetriever, RetrievalRequest
from ...knowledge.static_retriever import StaticKnowledgeRetriever
from ...llm import LLMProvider
from ...schemas.canonical_validator import assert_canonical_document
from ...schemas.generation import GenerateCvRequest, GenerateCvResult, GenerationReport
from ...yaml_layer.io import serialize_yaml
from .builder import build_canonical_document
from .evidence import build_candidate_evidence
from .gaps import detect_gaps
from .plan import build_generation_plan
from .sections import SectionGenerator

EventCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class CvGenerationPipeline:
    def __init__(
        self,
        provider: LLMProvider,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.jd_analyzer = JDAnalyzer(provider)
        self.section_generator = SectionGenerator(provider)
        self.retriever = retriever or StaticKnowledgeRetriever()

    async def generate(
        self,
        request: GenerateCvRequest,
        on_event: Optional[EventCallback] = None,
    ) -> GenerateCvResult:
        async def emit(event_type: str, data: Dict[str, Any]) -> None:
            if on_event:
                await on_event({"type": event_type, "data": data})

        async def progress(step: str) -> None:
            await emit("progress", {"step": step, "message": PROGRESS_MESSAGES[step]})

        await progress("normalize")
        gaps = detect_gaps(request)
        required_gaps = [gap for gap in gaps if gap.severity == "required"]
        if gaps:
            await emit("gap_report", {"gaps": [gap.model_dump(by_alias=True) for gap in gaps]})
        if required_gaps:
            return GenerateCvResult(
                status="needs_input",
                gaps=gaps,
                report=GenerationReport(
                    requestId=request.request_id,
                    generationId=request.generation_id,
                ),
            )

        await progress("evidence")
        evidence = build_candidate_evidence(request.profile)

        await progress("jd_analysis")
        jd = await self.jd_analyzer.analyze(
            request.job_description,
            request.options.language,
        )
        warnings: List[str] = []

        await progress("rag")
        knowledge_by_section: Dict[str, List[Dict[str, Any]]] = {}
        for section in ("summary", "experience", "projects"):
            retrieval_request = RetrievalRequest(
                query=request.job_description,
                section=section,
                industry=request.options.industry,
                language=request.options.language,
                seniority=jd.seniority,
                role_family=jd.role_family,
                keywords=jd.keywords,
            )
            try:
                retrieval = await self.retriever.retrieve(
                    retrieval_request,
                    top_k=RAG_TOP_K,
                )
            except Exception as exc:
                warnings.append(
                    f"Knowledge retrieval failed for {section}; continued without RAG: {exc}",
                )
                retrieval = await NullKnowledgeRetriever().retrieve(
                    retrieval_request,
                    top_k=RAG_TOP_K,
                )
            knowledge_by_section[section] = [
                chunk.model_dump() for chunk in retrieval.chunks
            ]

        plan = build_generation_plan(request.profile, evidence)
        await emit("progress", {
            "step": "plan",
            "message": PROGRESS_MESSAGES["plan"],
            "sections": plan.section_order,
        })

        await progress("generate")
        generated = await self.section_generator.generate(
            request,
            jd,
            evidence,
            knowledge_by_section,
            emit,
        )
        warnings.extend(generated.warnings)

        await progress("canonical")
        target_terms = " ".join(
            jd.required_skills + jd.preferred_skills + jd.keywords,
        ).lower()
        ordered_skills = sorted(
            request.profile.skills,
            key=lambda skill: (
                skill.name.lower() not in target_terms,
                skill.name.lower(),
            ),
        )
        document = build_canonical_document(
            request,
            generated.summary,
            generated.experience_highlights,
            generated.project_highlights,
            ordered_skills,
        )
        assert_canonical_document(document)
        cv_yaml = serialize_yaml({"cv": document["cv"]})
        canonical_text = str(document["cv"]).lower()
        missing_keywords = [
            keyword for keyword in jd.keywords
            if keyword.lower() not in canonical_text
        ]

        return GenerateCvResult(
            status="partial" if warnings else "success",
            document=document,
            cvYaml=cv_yaml,
            gaps=gaps,
            report=GenerationReport(
                requestId=request.request_id,
                generationId=request.generation_id,
                usedEvidenceIds=sorted(set(generated.used_evidence_ids)),
                missingJdKeywords=missing_keywords,
                warnings=warnings,
            ),
        )
