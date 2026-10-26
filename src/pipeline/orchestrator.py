"""
CV Tailoring Pipeline Orchestrator.

Implements the end-to-end 9-step pipeline:
  ① Validate Input
  ② Normalize Bonus & Directives
  ③ Attach to Sections & RAG Context
  ④ Detect Conflicts
  ⑤ Analyze Job Description (LLM)
  ⑥ Select Keywords & Fragments
  ⑦ Rewrite Highlights using STAR (LLM) for Experience & Projects & Objective
  ⑧ Anti-Hallucination Guard Verification
  ⑨ Export Clean YAML & Report
"""
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from ..guard.anti_hallucination import AntiHallucinationGuard
from ..industry.context import get_industry_context
from ..llm import LLMProvider
from ..llm.factory import get_llm_provider
from ..schemas.cv_input import CvInput, Experience, Project
from ..schemas.internal import (
    Constraint,
    ExperienceRewriteOutput,
    Fragment,
    JDProfile,
    ObjectiveRewriteOutput,
)
from ..schemas.proposal import (
    BonusInput,
    ChangeItem,
    ConflictItem,
    ControlConfig,
    CoreCvInput,
    CvReport,
)
from ..yaml_layer.io import serialize_yaml
from .prompts import (
    build_experience_rewrite_prompt,
    build_jd_analysis_prompt,
    build_objective_rewrite_prompt,
    build_project_rewrite_prompt,
)

logger = logging.getLogger(__name__)


class CvTailorPipeline:
    """
    Executes the CV Tailoring pipeline:
    Receives structured CvInput (from YAML, Markdown, or form wizard) and produces
    tailored renderable YAML + CvReport, with optional async real-time progress callbacks.
    """

    def __init__(self, control: Optional[ControlConfig] = None):
        self.control = control or ControlConfig()
        self.report = CvReport()

    # ── Legacy MVP helpers for backward compatibility ─────────────────────────

    def step1_validate_core(self, core: CoreCvInput) -> bool:
        if not core.name:
            raise ValueError("Core CV validation failed: 'name' is required.")
        return True

    def step2_normalize_bonus(self, bonus: BonusInput) -> Dict[str, Any]:
        return {
            "attached": [n for n in bonus.notes if n.attach_to],
            "general": [n for n in bonus.notes if not n.attach_to],
            "directives": bonus.directives,
            "references": bonus.references,
        }

    def step4_detect_conflicts(self, core: CoreCvInput, bonus: BonusInput):
        for note in bonus.notes:
            if "xung đột" in note.text.lower() or "conflict" in note.text.lower():
                self.report.conflicts.append(
                    ConflictItem(
                        field=note.attach_to or "general",
                        core_value="existing",
                        bonus_value=note.text,
                        flag="Mơ hồ/xung đột phát hiện giữa Bonus và Core",
                    )
                )

    def step8_check_hallucination(self, rewritten_bullet: str, sources: list[str]) -> bool:
        is_valid, unverified = AntiHallucinationGuard.verify_facts(rewritten_bullet, sources)
        if not is_valid:
            logger.warning("Anti-hallucination guard flagged unverified metrics: %s", unverified)
        return is_valid

    def run_mvp(
        self, core: CoreCvInput, bonus: BonusInput
    ) -> Tuple[Dict[str, Any], CvReport]:
        self.step1_validate_core(core)
        self.step2_normalize_bonus(bonus)
        self.step4_detect_conflicts(core, bonus)

        for note in bonus.notes:
            self.report.used_bonus.append(note.text)

        output_cv = core.model_dump()
        return output_cv, self.report

    # ── End-to-End Async Pipeline (Full Production Flow) ───────────────────────

    def normalize_bonus(self, bonus: Optional[BonusInput]) -> Tuple[List[Fragment], Constraint]:
        """Convert raw bonus notes to atomic Fragments and directives to Constraint."""
        if not bonus:
            return [], Constraint()

        fragments: List[Fragment] = []
        for idx, note in enumerate(bonus.notes):
            fragments.append(
                Fragment(
                    id=f"frag_{idx}",
                    text=note.text,
                    attach_to=note.attach_to,
                    target=note.attach_to,
                )
            )

        ban_terms: List[str] = []
        emphasize: List[str] = []
        tone = None

        for directive in bonus.directives:
            d_lower = directive.lower()
            if "không nhắc" in d_lower or "do not mention" in d_lower or "ban" in d_lower:
                for prefix in ["không nhắc", "do not mention", "ban"]:
                    if prefix in d_lower:
                        term = directive[d_lower.index(prefix) + len(prefix) :].strip(": ,\"'")
                        if term:
                            ban_terms.append(term)
            elif "nhấn mạnh" in d_lower or "emphasize" in d_lower or "highlight" in d_lower:
                for prefix in ["nhấn mạnh", "emphasize", "highlight"]:
                    if prefix in d_lower:
                        term = directive[d_lower.index(prefix) + len(prefix) :].strip(": ,\"'")
                        if term:
                            emphasize.append(term)
            elif "giọng" in d_lower or "tone" in d_lower:
                tone = directive.strip()

        constraint = Constraint(
            ban_terms=ban_terms,
            emphasize=emphasize,
            tone=tone,
            raw="; ".join(bonus.directives),
        )
        return fragments, constraint

    async def tailor(
        self,
        cv_input: CvInput,
        llm_provider: Optional[LLMProvider] = None,
        on_progress: Optional[Callable[[dict], Awaitable[None]]] = None,
    ) -> Tuple[str, CvReport, CvInput]:
        """
        Runs the full tailoring flow:
          1. Normalizes bonus & directives
          2. Analyzes JD
          3. Rewrites objective, experience, and project highlights using STAR
          4. Verifies via AntiHallucinationGuard
          5. Generates clean YAML and detailed report
        """
        async def _emit(step: str, message: str, data: Optional[dict] = None):
            if on_progress:
                payload = {"step": step, "message": message}
                if data:
                    payload.update(data)
                await on_progress(payload)

        await _emit("validate", "Validating CV and normalising inputs...")

        provider = llm_provider or get_llm_provider()
        control = cv_input.control
        locale = control.locale or "vi"

        # Step 2: Normalize bonus & constraints
        fragments, constraint = self.normalize_bonus(cv_input.bonus)

        # Step 3: Industry RAG context slot
        industry_context = get_industry_context(control.industry)

        # Step 5: JD Analysis if JD text is provided
        jd_profile: Optional[JDProfile] = None
        if cv_input.jd and cv_input.jd.strip():
            await _emit("jd_analysis", "Analyzing target Job Description...")
            try:
                jd_messages = build_jd_analysis_prompt(
                    jd_text=cv_input.jd,
                    target_position=cv_input.position,
                    locale=locale,
                )
                jd_profile = await provider.generate_structured(
                    schema=JDProfile,
                    messages=jd_messages,
                )
                logger.info(
                    "[Pipeline] JD analyzed: %d keywords, %d required skills",
                    len(jd_profile.keywords),
                    len(jd_profile.required_skills),
                )
                await _emit("jd_analysis", "JD analysis complete.", {
                    "keywords": jd_profile.keywords[:10],
                    "seniority": jd_profile.seniority,
                })
            except Exception as e:
                logger.warning("[Pipeline] JD analysis failed: %s; proceeding with direct tailoring", e)

        jd_keywords = jd_profile.keywords if jd_profile else []

        # Step 6a: Rewrite Objective if not locked
        updated_objective = cv_input.objective
        is_obj_locked = any(locked_path in ["objective", "summary"] for locked_path in control.locked)

        if not is_obj_locked and cv_input.objective:
            await _emit("objective", "Tailoring professional objective...")
            try:
                obj_prompt = build_objective_rewrite_prompt(
                    current_objective=cv_input.objective,
                    target_position=cv_input.position,
                    jd_keywords=jd_keywords,
                    industry_context=industry_context,
                    constraint=constraint,
                    locale=locale,
                )
                obj_out = await provider.generate_structured(
                    schema=ObjectiveRewriteOutput,
                    messages=obj_prompt,
                )
                candidate_obj = obj_out.objective.strip()

                is_valid, violations = AntiHallucinationGuard.verify_bullet(
                    output_text=candidate_obj,
                    source_texts=[cv_input.objective],
                    ban_terms=constraint.ban_terms,
                )
                if is_valid:
                    self.report.changes.append(
                        ChangeItem(
                            target="objective",
                            before=cv_input.objective,
                            after=candidate_obj,
                            source="Objective tailoring matching JD" if cv_input.jd else "Objective styling",
                        )
                    )
                    updated_objective = candidate_obj
                else:
                    logger.warning("[Pipeline] Guard rejected objective rewrite: %s", violations)
            except Exception as exc:
                logger.warning("[Pipeline] Failed to rewrite objective: %s", exc)

        # Step 6b & 7: Rewrite Experience highlights
        updated_experiences: List[Experience] = []
        used_fragment_ids = set()

        for exp_idx, exp in enumerate(cv_input.experience):
            path_prefix = f"experience[{exp_idx}]"
            is_locked = any(locked_path in path_prefix or locked_path == "experience" for locked_path in control.locked)
            if is_locked:
                logger.info("[Pipeline] Section %s is locked, keeping original", path_prefix)
                updated_experiences.append(exp)
                continue

            await _emit("experience", f"Tailoring experience at {exp.company}...", {"company": exp.company})

            attached_frags = [
                f for f in fragments if f.attach_to and (f.attach_to == path_prefix or f.attach_to in exp.company)
            ]
            if not attached_frags:
                attached_frags = [f for f in fragments if not f.attach_to]

            evidence_sources = list(exp.highlights) + [f.text for f in attached_frags]

            rewrite_messages = build_experience_rewrite_prompt(
                company=exp.company,
                title=exp.title,
                original_highlights=exp.highlights,
                target_position=cv_input.position,
                objective=updated_objective,
                fragments=attached_frags,
                constraint=constraint,
                jd_keywords=jd_keywords,
                industry_context=industry_context,
                locale=locale,
            )

            try:
                rewrite_out = await provider.generate_structured(
                    schema=ExperienceRewriteOutput,
                    messages=rewrite_messages,
                )
                new_bullets: List[str] = []

                for bullet_idx, original_bullet in enumerate(exp.highlights):
                    target_path = f"{path_prefix}.highlights[{bullet_idx}]"

                    if bullet_idx < len(rewrite_out.highlights):
                        candidate_bullet = rewrite_out.highlights[bullet_idx].text.strip()
                        is_valid, violations = AntiHallucinationGuard.verify_bullet(
                            output_text=candidate_bullet,
                            source_texts=evidence_sources,
                            ban_terms=constraint.ban_terms,
                        )

                        if is_valid:
                            new_bullets.append(candidate_bullet)
                            self.report.changes.append(
                                ChangeItem(
                                    target=target_path,
                                    before=original_bullet,
                                    after=candidate_bullet,
                                    source="STAR rewrite matching JD" if cv_input.jd else "STAR rewrite",
                                )
                            )
                            for f in attached_frags:
                                used_fragment_ids.add(f.id)
                        else:
                            logger.warning(
                                "[Pipeline] Guard rejected candidate for %s: %s; keeping original",
                                target_path,
                                violations,
                            )
                            new_bullets.append(original_bullet)
                    else:
                        new_bullets.append(original_bullet)

                exp_copy = exp.model_copy(update={"highlights": new_bullets})
                updated_experiences.append(exp_copy)

            except Exception as exc:
                logger.warning("[Pipeline] Error rewriting %s (%s); retaining original", path_prefix, exc)
                updated_experiences.append(exp)

        # Step 6c: Rewrite Projects highlights
        updated_projects: List[Project] = []
        for p_idx, proj in enumerate(cv_input.projects):
            path_prefix = f"projects[{p_idx}]"
            is_locked = any(locked_path in path_prefix or locked_path == "projects" for locked_path in control.locked)
            if is_locked or not proj.highlights:
                updated_projects.append(proj)
                continue

            await _emit("projects", f"Tailoring project: {proj.name}...", {"project": proj.name})

            proj_prompt = build_project_rewrite_prompt(
                project_name=proj.name,
                original_highlights=proj.highlights,
                tech_stack=proj.tech,
                target_position=cv_input.position,
                jd_keywords=jd_keywords,
                industry_context=industry_context,
                constraint=constraint,
                locale=locale,
            )

            try:
                proj_out = await provider.generate_structured(
                    schema=ExperienceRewriteOutput,
                    messages=proj_prompt,
                )
                new_proj_bullets: List[str] = []

                for b_idx, orig_b in enumerate(proj.highlights):
                    target_path = f"{path_prefix}.highlights[{b_idx}]"
                    if b_idx < len(proj_out.highlights):
                        cand_b = proj_out.highlights[b_idx].text.strip()
                        is_valid, _ = AntiHallucinationGuard.verify_bullet(
                            output_text=cand_b,
                            source_texts=proj.highlights + proj.tech,
                            ban_terms=constraint.ban_terms,
                        )
                        if is_valid:
                            new_proj_bullets.append(cand_b)
                            self.report.changes.append(
                                ChangeItem(
                                    target=target_path,
                                    before=orig_b,
                                    after=cand_b,
                                    source="Project STAR rewrite",
                                )
                            )
                        else:
                            new_proj_bullets.append(orig_b)
                    else:
                        new_proj_bullets.append(orig_b)

                updated_projects.append(proj.model_copy(update={"highlights": new_proj_bullets}))
            except Exception as exc:
                logger.warning("[Pipeline] Failed to rewrite project %s: %s", proj.name, exc)
                updated_projects.append(proj)

        # Record used vs unused bonus notes
        for f in fragments:
            if f.id in used_fragment_ids:
                self.report.used_bonus.append(f.text)
            else:
                self.report.unused_bonus.append(f.text)

        # Compute keyword match score if JD was analyzed
        if jd_keywords:
            full_tailored_text = " ".join(
                [updated_objective]
                + [h for e in updated_experiences for h in e.highlights]
                + [h for p in updated_projects for h in p.highlights]
            ).lower()

            matched_kws = [kw for kw in jd_keywords if kw.lower() in full_tailored_text]
            missing_kws = [kw for kw in jd_keywords if kw.lower() not in full_tailored_text]

            self.report.missing_jd_keywords = missing_kws
            total_kws = len(jd_keywords)
            self.report.match_score = round((len(matched_kws) / total_kws * 100), 1) if total_kws > 0 else 100.0

        # Create updated CvInput
        tailored_cv = cv_input.model_copy(
            update={
                "objective": updated_objective,
                "experience": updated_experiences,
                "projects": updated_projects,
                "bonus": None,  # Clean bonus from final rendered CV
                "jd": None,     # Clean JD from final rendered CV
            }
        )

        # Step 9: Serialize to clean YAML
        cv_dict = tailored_cv.model_dump(exclude_none=True)
        cv_yaml = serialize_yaml(cv_dict)

        await _emit("done", "CV tailoring finished successfully.", {
            "match_score": self.report.match_score,
            "changes_count": len(self.report.changes),
        })

        return cv_yaml, self.report, tailored_cv
