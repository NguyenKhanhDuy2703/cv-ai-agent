"""
Autonomous Agent Core Tailor Pipeline.

Executes canonical workflow:
Validate request
→ Extract Candidate Evidence
→ Analyze JD
→ Retrieve knowledge via KnowledgeRetriever (default: NullKnowledgeRetriever)
→ Plan Experience entries (iterating one Experience entry at a time)
→ Generate typed proposals with evidenceIds
→ Run deterministic guards (0% numeric fabrication tolerance, skill grounding, ban terms)
→ Build semantic patches
→ Apply accepted patches
→ Return TailorDiffReport with detailed proposal statuses & diffs
"""
import copy
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..schemas.canonical_dto import (
    CanonicalTailorRequest,
    PatchProposalReport,
    SemanticPatch,
    TailorDiffReport,
    compute_bullet_hash,
)
from ..schemas.canonical_validator import validate_canonical_document, DocumentValidationError
from ..schemas.patch_applier import apply_semantic_patches, is_path_locked, is_entry_or_section_locked
from ..core.evidence_extractor import extract_candidate_evidence
from ..core.jd_analyzer import JDAnalyzer, JDAnalysisOutput
from ..core.experience_writer import ExperienceWriter, ProposedBullet
from ..guard.deterministic_guard import DeterministicGuard
from ..knowledge.retriever_protocol import KnowledgeRetriever, RetrievalRequest
from ..knowledge.null_retriever import NullKnowledgeRetriever
from ..llm import LLMProvider
from ..llm.factory import get_llm_provider

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[Dict[str, Any]], Awaitable[None]]


class AgentTailorPipeline:
    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        retriever: Optional[KnowledgeRetriever] = None,
    ):
        self.provider = provider or get_llm_provider()
        self.retriever = retriever or NullKnowledgeRetriever()
        self.jd_analyzer = JDAnalyzer(provider=self.provider)
        self.experience_writer = ExperienceWriter(provider=self.provider)

    async def tailor_document(
        self,
        request: CanonicalTailorRequest,
        on_progress: Optional[ProgressCallback] = None,
    ) -> TailorDiffReport:
        run_id = request.requestId
        cv_id = request.cvId
        base_version = request.baseVersion
        doc = request.document
        options = request.options or {}
        language = getattr(options, "language", "vi")
        industry = getattr(options, "industry", "it_software")
        locked_paths = getattr(options, "lockedPaths", []) or []

        async def emit(step: str, data: Dict[str, Any]):
            if on_progress:
                payload = {
                    "type": step,
                    "runId": run_id,
                    "data": data,
                }
                try:
                    await on_progress(payload)
                except Exception as exc:
                    logger.debug("Progress callback failed: %s", exc)

        await emit("started", {"cvId": cv_id, "baseVersion": base_version})

        # Step 1: Validate input document
        is_valid, validation_errors = validate_canonical_document(doc)
        if not is_valid:
            await emit("failed", {"reason": "Document failed canonical validation", "errors": validation_errors})
            return TailorDiffReport(
                requestId=run_id,
                cvId=cv_id,
                baseVersion=base_version,
                status="failed",
                summary=f"Input document validation failed: {'; '.join(validation_errors[:3])}",
                appliedDocument=None,
            )

        await emit("input_validated", {"status": "valid"})

        # Step 2: Extract authoritative Candidate Evidence
        evidence_store = extract_candidate_evidence(doc)

        # Step 3: Analyze target JD
        jd_profile: JDAnalysisOutput = await self.jd_analyzer.analyze(
            jd_text=request.jobDescription,
            language=language,
        )
        await emit("jd_analyzed", {
            "seniority": jd_profile.seniority,
            "role_family": jd_profile.role_family,
            "required_skills": jd_profile.required_skills,
            "keywords": jd_profile.keywords,
        })

        # Step 4: Knowledge Retrieval
        retrieval_request = RetrievalRequest(
            query=request.jobDescription,
            section="experience",
            industry=industry,
            language=language,
            seniority=jd_profile.seniority,
            role_family=jd_profile.role_family,
            keywords=jd_profile.keywords,
        )
        retrieval_result = await self.retriever.retrieve(retrieval_request, top_k=5)
        await emit("retrieval_completed", {
            "retriever": retrieval_result.retriever_name,
            "chunksCount": len(retrieval_result.chunks),
        })

        # Step 5: Process Experience entries one by one
        target_doc = doc.get("document", doc)
        cv = target_doc.get("cv", {})
        sections = cv.get("sections", [])

        proposals_report: List[PatchProposalReport] = []
        accepted_patches: List[SemanticPatch] = []

        knowledge_dicts = [c.model_dump() for c in retrieval_result.chunks]

        for s_idx, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            if section.get("entryType") != "Experience":
                continue

            sec_id = section.get("id", f"sec-{s_idx}")
            entries = section.get("entries", []) or []

            for e_idx, entry in enumerate(entries):
                if not isinstance(entry, dict) or entry.get("type") != "Experience":
                    continue

                ent_id = entry.get("id", f"ent-{e_idx}")
                highlights = entry.get("highlights", []) or []
                if not highlights:
                    continue

                # Check if entire entry or section is locked
                if is_entry_or_section_locked(sec_id, ent_id, locked_paths):
                    # Locked, keep unchanged
                    for h_idx, hl in enumerate(highlights):
                        patch = SemanticPatch(
                            sectionId=sec_id,
                            entryId=ent_id,
                            index=h_idx,
                            beforeHash=compute_bullet_hash(hl),
                            value=hl,
                        )
                        proposals_report.append(
                            PatchProposalReport(
                                patch=patch,
                                originalValue=hl,
                                status="unchanged",
                                reason="Entry is locked by user preference",
                            )
                        )
                    continue

                await emit("section_started", {
                    "sectionId": sec_id,
                    "entryId": ent_id,
                    "company": entry.get("company", ""),
                    "position": entry.get("position", ""),
                })

                # Call ExperienceWriter
                try:
                    rewrite_output = await self.experience_writer.rewrite_entry(
                        entry=entry,
                        jd=jd_profile,
                        evidence_store=evidence_store,
                        knowledge_chunks=knowledge_dicts,
                        language=language,
                        instruction=request.instruction or "",
                    )
                except Exception as exc:
                    logger.error("Experience rewrite error on entry %s: %s", ent_id, exc)
                    rewrite_output = None

                # Process proposals for this entry (bound to valid highlight indices)
                proposed_by_idx = {
                    p.index: p for p in (rewrite_output.proposals if rewrite_output else [])
                    if 0 <= p.index < len(highlights)
                }

                for h_idx, original_hl in enumerate(highlights):
                    original_hash = compute_bullet_hash(original_hl)

                    if is_path_locked(sec_id, ent_id, h_idx, locked_paths):
                        patch = SemanticPatch(
                            sectionId=sec_id,
                            entryId=ent_id,
                            index=h_idx,
                            beforeHash=original_hash,
                            value=original_hl,
                        )
                        proposals_report.append(
                            PatchProposalReport(
                                patch=patch,
                                originalValue=original_hl,
                                status="unchanged",
                                reason="Highlight bullet path is locked",
                            )
                        )
                        continue

                    prop: Optional[ProposedBullet] = proposed_by_idx.get(h_idx)
                    if not prop or not prop.text.strip():
                        # Unchanged
                        patch = SemanticPatch(
                            sectionId=sec_id,
                            entryId=ent_id,
                            index=h_idx,
                            beforeHash=original_hash,
                            value=original_hl,
                        )
                        proposals_report.append(
                            PatchProposalReport(
                                patch=patch,
                                originalValue=original_hl,
                                status="unchanged",
                                reason="No rewrite proposal generated by model",
                            )
                        )
                        continue

                    await emit("patch_proposed", {
                        "sectionId": sec_id,
                        "entryId": ent_id,
                        "index": h_idx,
                        "value": prop.text,
                    })

                    # Run deterministic guards with entry-level grounding
                    guard_result = DeterministicGuard.verify(
                        proposed_text=prop.text,
                        evidence_ids=prop.evidence_ids,
                        original_bullet=original_hl,
                        evidence_store=evidence_store,
                        language=language,
                        current_entry_id=ent_id,
                        entry_dates={
                            "start_date": entry.get("start_date"),
                            "end_date": entry.get("end_date") or entry.get("date"),
                        },
                    )

                    patch = SemanticPatch(
                        sectionId=sec_id,
                        entryId=ent_id,
                        index=h_idx,
                        beforeHash=original_hash,
                        value=prop.text if guard_result.is_valid else original_hl,
                        evidenceIds=prop.evidence_ids if guard_result.is_valid else [],
                        knowledgeChunkIds=prop.knowledge_chunk_ids if guard_result.is_valid else [],
                    )

                    if guard_result.is_valid:
                        accepted_patches.append(patch)
                        proposals_report.append(
                            PatchProposalReport(
                                patch=patch,
                                originalValue=original_hl,
                                status="accepted",
                                reason=prop.rationale or "Passed deterministic quality & factuality guards",
                                guardChecks=guard_result.checks,
                            )
                        )
                        await emit("validation_completed", {
                            "sectionId": sec_id,
                            "entryId": ent_id,
                            "index": h_idx,
                            "status": "accepted",
                        })
                    else:
                        proposals_report.append(
                            PatchProposalReport(
                                patch=patch,
                                originalValue=original_hl,
                                status="rejected",
                                reason="; ".join(guard_result.rejection_reasons),
                                guardChecks=guard_result.checks,
                            )
                        )
                        await emit("validation_completed", {
                            "sectionId": sec_id,
                            "entryId": ent_id,
                            "index": h_idx,
                            "status": "rejected",
                            "reasons": guard_result.rejection_reasons,
                        })

        # Apply accepted patches to preview updated document
        applied_doc, patch_errors = apply_semantic_patches(
            document=doc,
            patches=accepted_patches,
            locked_paths=locked_paths,
        )

        # Determine overall pipeline status
        total_props = len(proposals_report)
        accepted_cnt = len(accepted_patches)
        rejected_cnt = sum(1 for p in proposals_report if p.status == "rejected")

        if patch_errors:
            pipeline_status = "degraded"
            summary_msg = f"Patch application encountered errors: {'; '.join(patch_errors)}"
            final_doc = doc
        elif accepted_cnt == 0 and total_props > 0:
            pipeline_status = "degraded"
            summary_msg = "All proposals were rejected by factuality guards or locked. Original CV preserved."
            final_doc = doc
        elif rejected_cnt > 0:
            pipeline_status = "partial"
            summary_msg = f"Tailored {accepted_cnt} bullets successfully. {rejected_cnt} proposals rejected for quality/factuality."
            final_doc = applied_doc
        else:
            pipeline_status = "success"
            summary_msg = f"All {accepted_cnt} bullets optimized successfully with complete evidence grounding."
            final_doc = applied_doc

        report = TailorDiffReport(
            requestId=run_id,
            cvId=cv_id,
            baseVersion=base_version,
            status=pipeline_status,
            acceptedPatches=accepted_patches,
            proposals=proposals_report,
            summary=summary_msg,
            appliedDocument=final_doc,
        )

        await emit("completed", {
            "status": pipeline_status,
            "acceptedCount": accepted_cnt,
            "rejectedCount": rejected_cnt,
            "summary": summary_msg,
        })

        return report
