"""
Internal pipeline types — not exposed in the API.

These types represent data flowing between pipeline steps.
Pipeline functions are typed with these; the API only sees CvInput / CvOutput.

Data flow:
  CvInput
    → collect_leaves()   → List[Leaf]         (YAML layer)
    → normalize_bonus()  → List[Fragment]      (step 2)
    → parse_directives() → Constraint          (step 2)
    → rewrite()          → List[RewriteResult] (step 7, via LLM)
    → guard.verify()     → accepted / rejected
    → patch() + export() → cv.yaml + report
"""
from typing import Optional
from pydantic import BaseModel, Field


class Leaf(BaseModel):
    """
    A rewritable text node extracted from the Core CV YAML tree.

    `path` is the stable address used to patch the tree after rewriting.
    Examples: 'experience[0].highlights[1]', 'objective'
    """
    path: str = Field(..., description="Stable dot-bracket path within the YAML tree")
    text: str = Field(..., description="Original text content at this path")
    locked: bool = Field(default=False, description="True if this path is in control.locked")


class Fragment(BaseModel):
    """
    One atomic piece of information extracted from a bonus note.

    A single bonus note may contain multiple ideas; each idea becomes
    one Fragment so the LLM gets focused, single-purpose inputs.
    """
    id: str = Field(..., description="Stable identifier, e.g. 'frag_0', 'frag_1'")
    text: str = Field(..., description="The single-idea content of this fragment")
    attach_to: Optional[str] = Field(
        default=None,
        description="User-specified attachment path, e.g. 'experience[0]'",
    )
    target: Optional[str] = Field(
        default=None,
        description="Resolved target section after LLM or rule-based placement",
    )
    unplaced: bool = Field(
        default=False,
        description="True when no target could be determined; reported in the output report",
    )


class Constraint(BaseModel):
    """
    A structured representation of user directives.

    Directives are parsed from free-text strings like:
      'Do not mention Company Y'  → ban_terms=['Company Y']
      'Emphasise BIM'             → emphasize=['BIM']
      'Use a confident tone'      → tone='confident'

    Used both in the LLM prompt (to guide writing) and in the Guard
    (to enforce ban_terms on the output).
    """
    ban_terms: list[str] = Field(
        default_factory=list,
        description="Terms that must not appear in the rewritten CV",
    )
    emphasize: list[str] = Field(
        default_factory=list,
        description="Terms or skills to highlight in the rewritten CV",
    )
    tone: Optional[str] = Field(
        default=None,
        description="Writing tone, e.g. 'confident', 'humble', 'concise'",
    )
    raw: str = Field(default="", description="Original directive text before parsing")


class RewriteResult(BaseModel):
    """
    What the LLM returns for one rewritable leaf.

    The LLM never writes YAML — it returns structured text.
    Python code patches `path` in the YAML tree with `text`.
    `source_ids` links the new text back to Leaf ids and Fragment ids,
    allowing the Guard and the report to verify provenance.
    """
    path: str = Field(..., description="Target path to patch in the YAML tree")
    text: str = Field(..., description="New text produced by the LLM")
    source_ids: list[str] = Field(
        ...,
        description="IDs of Leaf or Fragment objects that support this text",
    )


class JDProfile(BaseModel):
    """
    Structured analysis of a target Job Description.
    """
    keywords: list[str] = Field(default_factory=list, description="Primary technical and industry keywords")
    required_skills: list[str] = Field(default_factory=list, description="Must-have qualifications or competencies")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    seniority: Optional[str] = Field(default=None, description="Expected seniority level (e.g. Junior, Mid, Senior, Lead)")
    summary: Optional[str] = Field(default=None, description="Brief summary of the target role expectations")


class RewriteBullet(BaseModel):
    """
    One rewritten bullet item with provenance.
    """
    text: str = Field(..., description="Rewritten bullet point text in STAR framework")
    source_ids: list[str] = Field(default_factory=list, description="IDs of Leaf or Fragment supporting this bullet")


class ExperienceRewriteOutput(BaseModel):
    """
    LLM output for rewriting highlights of a single experience or project entry.
    """
    highlights: list[RewriteBullet] = Field(..., description="Rewritten bullet points matching exact input count")


class ObjectiveRewriteOutput(BaseModel):
    """
    LLM output for rewriting candidate's career objective or professional summary.
    """
    objective: str = Field(..., description="Tailored professional summary aligned with target role and JD")


