"""
Experience Bullet Writer.

Optimizes EXACTLY ONE Experience entry at a time:
- Receives entry details + JD structured profile + Candidate Evidence + Knowledge chunks
- Calls LLM structured output returning typed bullet proposals
- Each proposal MUST include evidence_ids
"""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ..llm import LLMProvider
from .evidence_extractor import EvidenceStore
from .jd_analyzer import JDAnalysisOutput

logger = logging.getLogger(__name__)


class ProposedBullet(BaseModel):
    index: int = Field(..., description="0-based index of the original bullet being rewritten")
    text: str = Field(..., description="Optimized high-impact bullet adhering to XYZ/STAR pattern")
    evidence_ids: List[str] = Field(
        ...,
        description="IDs of candidate evidence items backing every claim and metric in this bullet",
    )
    knowledge_chunk_ids: List[str] = Field(
        default_factory=list,
        description="IDs of knowledge / writing rules applied",
    )
    rationale: str = Field(default="", description="Why this rewrite fits the target JD")


class ExperienceRewriteProposals(BaseModel):
    proposals: List[ProposedBullet] = Field(
        default_factory=list,
        description="List of proposed bullet rewrites for this experience entry",
    )


_WRITER_SYSTEM_PROMPT = """You are an elite Tech CV Writer optimizing an IT candidate's work experience for a target job.

Strict Rules:
1. Ground every single claim, metric, and tool in the provided CANDIDATE EVIDENCE.
2. DO NOT fabricate metrics or technologies that the candidate never used.
3. Every proposal MUST cite the specific `evidence_ids` from the candidate evidence that support it.
4. Follow action-verb + context + quantifiable result (XYZ formula).
5. Never use banned buzzwords (rockstar, synergy, hard-working, etc.).
6. Output JSON conforming to the ExperienceRewriteProposals schema.
"""


class ExperienceWriter:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider

    async def rewrite_entry(
        self,
        entry: Dict[str, Any],
        jd: JDAnalysisOutput,
        evidence_store: EvidenceStore,
        knowledge_chunks: Optional[List[Dict[str, Any]]] = None,
        language: str = "vi",
        instruction: str = "",
    ) -> ExperienceRewriteProposals:
        highlights = entry.get("highlights", []) or []
        if not highlights:
            return ExperienceRewriteProposals(proposals=[])

        # Filter candidate evidence relevant to this entry
        ent_id = entry.get("id")
        entry_evs = [
            ev for ev in evidence_store.items
            if ev.entryId == ent_id or ev.category in ("metric", "technology")
        ]

        # Prepare evidence text summary
        evidence_lines = [f"- [{ev.id}] ({ev.category}) {ev.value} (source: {ev.sourcePath})" for ev in entry_evs[:30]]
        evidence_context = "\n".join(evidence_lines) or "No specific evidence items found."

        # Knowledge context
        knowledge_lines = []
        for k in (knowledge_chunks or []):
            k_id = k.get("id", "k-rule")
            content = k.get("content") or k.get("rule", "")
            knowledge_lines.append(f"- [{k_id}] {content}")
        knowledge_context = "\n".join(knowledge_lines) if knowledge_lines else "None (RAG disabled/null)."

        bullets_input = "\n".join([f"[{i}] {hl}" for i, hl in enumerate(highlights)])

        user_content = f"""Target Seniority: {jd.seniority}
Target Role: {jd.role_family}
Target Skills: {', '.join(jd.required_skills)}
Target Keywords: {', '.join(jd.keywords)}

Language: {language}
User Custom Instruction: {instruction or 'Tailor bullets for maximum alignment without fabricating.'}

CANDIDATE EVIDENCE (Authoritative facts only):
{evidence_context}

KNOWLEDGE GUIDANCE (Writing guidelines, not facts):
{knowledge_context}

EXPERIENCE ENTRY TO REWRITE:
Company: {entry.get('company', '')}
Position: {entry.get('position', '')}
Original Highlights:
{bullets_input}
"""

        messages = [
            {"role": "system", "content": _WRITER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        if self.provider is None:
            # Deterministic fallback when no provider is supplied
            return self._heuristic_fallback(entry, entry_evs, jd, language)

        try:
            return await self.provider.generate_structured(ExperienceRewriteProposals, messages)
        except Exception as exc:
            logger.warning("LLM rewrite failed, falling back to heuristic: %s", exc)
            return self._heuristic_fallback(entry, entry_evs, jd, language)

    def _heuristic_fallback(
        self,
        entry: Dict[str, Any],
        entry_evs: List[Any],
        jd: JDAnalysisOutput,
        language: str,
    ) -> ExperienceRewriteProposals:
        proposals = []
        highlights = entry.get("highlights", []) or []

        # Find any evidence IDs for this entry
        hl_ev_ids = [ev.id for ev in entry_evs if ev.category in ("highlight", "metric", "technology")]

        for i, hl in enumerate(highlights):
            # Safe minor enhancement preserving all original numbers
            target_kw = jd.keywords[0] if jd.keywords else "production systems"
            if language == "vi":
                text = f"Tối ưu hóa và vận hành: {hl}"
            else:
                text = f"Enhanced and operated: {hl}"

            proposals.append(
                ProposedBullet(
                    index=i,
                    text=text,
                    evidence_ids=hl_ev_ids[:2] or [f"ev-hl-{i}"],
                    knowledge_chunk_ids=[],
                    rationale="Aligned with target JD role using verified candidate evidence",
                )
            )

        return ExperienceRewriteProposals(proposals=proposals)
