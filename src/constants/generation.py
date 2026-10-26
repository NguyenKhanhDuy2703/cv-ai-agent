"""Stable internal values for the Generate CV pipeline."""

DEFAULT_LANGUAGE = "vi"
DEFAULT_INDUSTRY = "it_software"
DEFAULT_TEMPLATE_SLUG = "classic"
RAG_TOP_K = 5

PROGRESS_MESSAGES = {
    "normalize": "Normalizing the candidate profile.",
    "evidence": "Building candidate evidence.",
    "jd_analysis": "Analyzing the job description.",
    "rag": "Retrieving CV writing guidance.",
    "plan": "Planning CV sections and evidence usage.",
    "generate": "Generating CV sections.",
    "canonical": "Building and validating the canonical CV document.",
}
