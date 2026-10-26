"""
Prompt templates and builders for CV tailoring pipeline.
Boundary markers are enforced to protect against prompt injection from user bonus notes or JD.
"""
from typing import List, Optional
from ..schemas.internal import Constraint, Fragment


def build_jd_analysis_prompt(jd_text: str, target_position: str, locale: str = "vi") -> list[dict[str, str]]:
    lang_name = "Vietnamese" if locale == "vi" else "English"
    system_msg = (
        f"You are a Senior Technical Recruiter and ATS Optimization Expert. "
        f"Analyze the following Job Description for the target role '{target_position}'. "
        f"Extract key skills, required technologies, preferred qualifications, and seniority level. "
        f"Respond strictly in JSON matching the requested schema. Provide your analysis in {lang_name}."
    )
    user_msg = (
        f"<TARGET_POSITION>\n{target_position}\n</TARGET_POSITION>\n\n"
        f"<JOB_DESCRIPTION>\n{jd_text}\n</JOB_DESCRIPTION>\n\n"
        f"Extract all technical keywords, hard requirements, and seniority expectations."
    )
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def build_experience_rewrite_prompt(
    company: str,
    title: str,
    original_highlights: List[str],
    target_position: str,
    objective: str,
    fragments: List[Fragment],
    constraint: Optional[Constraint] = None,
    jd_keywords: Optional[List[str]] = None,
    industry_context: Optional[str] = None,
    locale: str = "vi",
) -> list[dict[str, str]]:
    lang_name = "Vietnamese" if locale == "vi" else "English"
    count = len(original_highlights)

    system_msg = (
        f"You are an Elite Resume Writer specializing in ATS optimization and the STAR method "
        f"(Situation, Task, Action, Result). "
        f"Your task is to rewrite the work experience highlights for a candidate applying for '{target_position}'.\n\n"
        f"STRICT RULES:\n"
        f"1. You MUST output EXACTLY {count} rewritten highlight bullets.\n"
        f"2. Write in {lang_name}.\n"
        f"3. FACTUAL INTEGRITY (ANTI-HALLUCINATION): You must NEVER invent new metrics, percentages, dollar amounts, "
        f"technologies, or achievements that are not explicitly stated in the provided user data.\n"
        f"4. Weave in target keywords naturally ONLY if supported by the user's actual background.\n"
        f"5. Respect user constraints (ban terms, tone, emphasis)."
    )

    # Format fragments
    frag_texts = [f"- [{f.id}] {f.text}" for f in fragments]
    frag_block = "\n".join(frag_texts) if frag_texts else "None provided."

    # Format original bullets
    bullet_texts = [f"- {b}" for b in original_highlights]
    bullet_block = "\n".join(bullet_texts)

    # Format keywords
    kw_block = ", ".join(jd_keywords[:25]) if jd_keywords else "None"

    # Format constraints
    ban_block = ", ".join(constraint.ban_terms) if (constraint and constraint.ban_terms) else "None"
    tone_str = constraint.tone if (constraint and constraint.tone) else "Professional, impactful, concise"

    user_msg = (
        f"<CONTEXT>\n"
        f"Target Position: {target_position}\n"
        f"Candidate Objective: {objective}\n"
        f"Industry Context: {industry_context or 'General'}\n"
        f"Tone: {tone_str}\n"
        f"Forbidden Terms: {ban_block}\n"
        f"Target JD Keywords: {kw_block}\n"
        f"</CONTEXT>\n\n"
        f"<ORIGINAL_EXPERIENCE>\n"
        f"Company: {company}\n"
        f"Role: {title}\n"
        f"Current Highlights ({count} items):\n{bullet_block}\n"
        f"</ORIGINAL_EXPERIENCE>\n\n"
        f"<USER_SUPPLEMENTARY_NOTES>\n{frag_block}\n</USER_SUPPLEMENTARY_NOTES>\n\n"
        f"Rewrite each of the {count} highlights according to STAR. Return exactly {count} bullets."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def build_objective_rewrite_prompt(
    current_objective: str,
    target_position: str,
    jd_keywords: Optional[List[str]] = None,
    industry_context: Optional[str] = None,
    constraint: Optional[Constraint] = None,
    locale: str = "vi",
) -> list[dict[str, str]]:
    lang_name = "Vietnamese" if locale == "vi" else "English"
    system_msg = (
        f"You are a Senior Career Coach and Resume Strategist. "
        f"Rewrite the candidate's career objective / professional summary to strongly target the position '{target_position}'.\n\n"
        f"RULES:\n"
        f"1. Write 2-3 impactful, concise sentences in {lang_name}.\n"
        f"2. Integrate relevant keywords naturally without keyword stuffing.\n"
        f"3. FACTUAL INTEGRITY: Do NOT invent unevidenced degrees, years of experience, or skills not in the original text.\n"
        f"4. Respect tone and avoid forbidden terms."
    )

    kw_block = ", ".join(jd_keywords[:20]) if jd_keywords else "None"
    ban_block = ", ".join(constraint.ban_terms) if (constraint and constraint.ban_terms) else "None"
    tone_str = constraint.tone if (constraint and constraint.tone) else "Professional, goal-oriented"

    user_msg = (
        f"<CONTEXT>\n"
        f"Target Position: {target_position}\n"
        f"Industry Context: {industry_context or 'General'}\n"
        f"Tone: {tone_str}\n"
        f"Forbidden Terms: {ban_block}\n"
        f"Target JD Keywords: {kw_block}\n"
        f"</CONTEXT>\n\n"
        f"<CURRENT_OBJECTIVE>\n{current_objective}\n</CURRENT_OBJECTIVE>\n\n"
        f"Rewrite this summary to align with the target position and key skills."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def build_project_rewrite_prompt(
    project_name: str,
    original_highlights: List[str],
    tech_stack: List[str],
    target_position: str,
    jd_keywords: Optional[List[str]] = None,
    industry_context: Optional[str] = None,
    constraint: Optional[Constraint] = None,
    locale: str = "vi",
) -> list[dict[str, str]]:
    lang_name = "Vietnamese" if locale == "vi" else "English"
    count = len(original_highlights)

    system_msg = (
        f"You are an Elite Resume Writer specializing in STAR method optimization. "
        f"Rewrite the bullet points for the project '{project_name}' applying for '{target_position}'.\n\n"
        f"RULES:\n"
        f"1. Output EXACTLY {count} rewritten highlight bullets in {lang_name}.\n"
        f"2. Highlight engineering challenges, actions, and quantifiable impacts.\n"
        f"3. ZERO HALLUCINATION: Do NOT invent unevidenced metrics or tools.\n"
        f"4. Weave in matching JD keywords where evidenced."
    )

    bullet_texts = [f"- {b}" for b in original_highlights]
    bullet_block = "\n".join(bullet_texts)
    tech_block = ", ".join(tech_stack) if tech_stack else "Unspecified"
    kw_block = ", ".join(jd_keywords[:20]) if jd_keywords else "None"
    ban_block = ", ".join(constraint.ban_terms) if (constraint and constraint.ban_terms) else "None"

    user_msg = (
        f"<CONTEXT>\n"
        f"Target Position: {target_position}\n"
        f"Industry Context: {industry_context or 'General'}\n"
        f"Forbidden Terms: {ban_block}\n"
        f"Target JD Keywords: {kw_block}\n"
        f"</CONTEXT>\n\n"
        f"<ORIGINAL_PROJECT>\n"
        f"Project Name: {project_name}\n"
        f"Technologies: {tech_block}\n"
        f"Highlights ({count} items):\n{bullet_block}\n"
        f"</ORIGINAL_PROJECT>\n\n"
        f"Rewrite each of the {count} highlights according to STAR. Return exactly {count} bullets."
    )

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

