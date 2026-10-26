"""
Industry context plugin loader (RAG knowledge packs).
Loads domain terminology, action verbs, and STAR phrasing guidance.
"""
from pathlib import Path
from typing import Optional

_PACKS_DIR = Path(__file__).parent / "packs"
_CACHE: dict[str, str] = {}

# Alias mapping for user convenience and robust matching
_INDUSTRY_ALIASES = {
    # IT & Software
    "it": "it_software",
    "software": "it_software",
    "tech": "it_software",
    "it_software": "it_software",
    "it-software": "it_software",
    "cntt": "it_software",
    "backend": "it_software",
    "frontend": "it_software",
    "devops": "it_software",

    # Architecture, BIM & Construction
    "architecture": "architecture_construction",
    "bim": "architecture_construction",
    "construction": "architecture_construction",
    "aec": "architecture_construction",
    "architecture_construction": "architecture_construction",
    "architecture-construction": "architecture_construction",
    "architecture_bim": "architecture_construction",
    "kiến trúc": "architecture_construction",
    "xây dựng": "architecture_construction",

    # Data & AI
    "data": "data_ai",
    "ai": "data_ai",
    "data_ai": "data_ai",
    "data-ai": "data_ai",
    "ml": "data_ai",
    "machine_learning": "data_ai",
}


def get_industry_context(industry: Optional[str] = None) -> str:
    """
    Loads and returns industry knowledge context from markdown packs.
    Returns empty string if industry is None, empty, or not found.
    """
    if not industry or not industry.strip():
        return ""

    key = industry.strip().lower().replace(" ", "_")
    canonical_name = _INDUSTRY_ALIASES.get(key)
    if not canonical_name:
        # Try direct file match
        canonical_name = key

    if canonical_name in _CACHE:
        return _CACHE[canonical_name]

    pack_file = _PACKS_DIR / f"{canonical_name}.md"
    if pack_file.exists():
        try:
            content = pack_file.read_text(encoding="utf-8")
            _CACHE[canonical_name] = content
            return content
        except Exception:
            return ""

    return ""
