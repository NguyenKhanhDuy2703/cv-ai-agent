"""
Markdown CV Parser.
Converts structured/semi-structured Markdown text into a validated CvInput model.
"""
import re
from typing import List, Optional

from ..schemas.cv_input import CvInput, Education, Experience, Project


def parse_markdown_to_cv_input(markdown_text: str) -> CvInput:
    """
    Parses Markdown text into a structured CvInput model using rule-based extraction.
    """
    lines = [line.strip() for line in markdown_text.splitlines()]
    if not lines:
        raise ValueError("Provided Markdown text is empty.")

    # 1. Extract Name (typically first `# ` header)
    name = None
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            candidate = line.lstrip("# ").strip()
            if candidate:
                name = candidate
                break

    if not name:
        # Fallback: check first non-empty line that is NOT a section header or bullet point
        section_keywords = ["experience", "education", "project", "skill", "objective", "summary", "kinh nghiệm", "học vấn"]
        for line in lines:
            if line and not line.startswith("## ") and not line.startswith(("- ", "* ", "• ")):
                candidate = line.strip("# *_-")
                if candidate and not any(kw in candidate.lower() for kw in section_keywords):
                    name = candidate
                    break

    if not name:
        raise ValueError("Could not extract candidate name from Markdown.")

    # 2. Extract Target Position & Objective from preamble or specific headers
    position = "Professional"
    objective = ""

    pos_match = re.search(r"(?:^|\n)\*\*(?:Target )?(?:Position|Chức danh|Vị trí):\*\*\s*(.+)", markdown_text, re.IGNORECASE)
    if pos_match:
        position = pos_match.group(1).strip()
    else:
        # Check if the line right after name header is a bold headline or subtitle
        name_idx = -1
        for i, line in enumerate(lines):
            if name and name in line and line.startswith("#"):
                name_idx = i
                break
        if name_idx >= 0:
            for next_line in lines[name_idx + 1:]:
                if not next_line:
                    continue
                if next_line.startswith("##"):
                    break
                bold_match = re.match(r"^\*{1,2}([^*]+)\*{1,2}$", next_line)
                if bold_match:
                    cand_pos = bold_match.group(1).strip()
                    if cand_pos and not any(kw in cand_pos.lower() for kw in ["email", "phone", "contact", "http", "@"]):
                        position = cand_pos
                        break
                elif not any(kw in next_line.lower() for kw in ["email", "phone", "contact", "http", "@", "|"]):
                    position = next_line.strip()
                    break

    obj_match = re.search(r"\*\*Objective:\*\*\s*(.+)", markdown_text, re.IGNORECASE)
    if obj_match:
        objective = obj_match.group(1).strip()

    # 3. Split into sections by `## ` headers
    sections: dict[str, str] = {}
    current_section = "preamble"
    section_content: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if section_content:
                sections[current_section] = "\n".join(section_content)
                section_content = []
            current_section = line.lstrip("# ").strip().lower()
        else:
            section_content.append(line)

    if section_content:
        sections[current_section] = "\n".join(section_content)

    # If objective wasn't in preamble, check section
    for sec_name, content in sections.items():
        if any(k in sec_name for k in ["objective", "summary", "tóm tắt", "mục tiêu"]):
            if not objective:
                objective = content.strip()

    if not objective:
        objective = f"Experienced {position} seeking new professional opportunities."

    # 4. Parse Work Experience
    experiences: List[Experience] = []
    exp_content = ""
    for sec_name, content in sections.items():
        if any(k in sec_name for k in ["experience", "kinh nghiệm", "work"]):
            exp_content = content
            break

    if exp_content:
        # Split by `### ` entries
        sub_entries = re.split(r"\n###\s+", "\n" + exp_content)
        for entry in sub_entries:
            entry = entry.strip()
            if not entry:
                continue

            entry_lines = [l.strip() for l in entry.splitlines() if l.strip()]
            header = entry_lines[0].lstrip("# ").strip()

            company = header
            title = position
            # Match company — title or company - title or company | title
            if "—" in header:
                parts = header.split("—", 1)
                company, title = parts[0].strip(), parts[1].strip()
            elif " - " in header:
                parts = header.split(" - ", 1)
                company, title = parts[0].strip(), parts[1].strip()
            elif " | " in header:
                parts = header.split(" | ", 1)
                company, title = parts[0].strip(), parts[1].strip()
            elif " at " in header.lower():
                parts = re.split(r"\s+at\s+", header, flags=re.IGNORECASE)
                title, company = parts[0].strip(), parts[1].strip()


            # Date range from italicized line
            start_date = "2020"
            end_date = None
            date_match = re.search(r"\*([^*]+)\*", entry)
            if date_match:
                dates = date_match.group(1).split("-")
                start_date = dates[0].strip()
                if len(dates) > 1 and "present" not in dates[1].lower() and "nay" not in dates[1].lower():
                    end_date = dates[1].strip()

            # Highlights bullets
            bullets = [
                re.sub(r"^[-*•]\s*", "", l)
                for l in entry_lines
                if l.startswith(("- ", "* ", "• "))
            ]

            if not bullets:
                bullets = [l for l in entry_lines[1:] if not l.startswith("*")]

            if bullets:
                experiences.append(
                    Experience(
                        company=company,
                        title=title,
                        start=start_date,
                        end=end_date,
                        highlights=bullets,
                    )
                )

    if not experiences:
        experiences = [
            Experience(
                company="Independent",
                title=position,
                start="2020",
                highlights=["Demonstrated expertise in relevant projects."],
            )
        ]

    # 5. Parse Education
    educations: List[Education] = []
    edu_content = ""
    for sec_name, content in sections.items():
        if any(k in sec_name for k in ["education", "học vấn", "đào tạo"]):
            edu_content = content
            break

    if edu_content:
        sub_edu = re.split(r"\n###\s+", "\n" + edu_content)
        for entry in sub_edu:
            entry = entry.strip()
            if not entry:
                continue
            edu_lines = [l.strip() for l in entry.splitlines() if l.strip()]
            inst = edu_lines[0].lstrip("# ").strip()
            degree = "Bachelor's Degree"
            year = None

            for l in edu_lines[1:]:
                clean_l = re.sub(r"^[-*•]\s*", "", l)
                if any(deg_kw in clean_l.lower() for deg_kw in ["bachelor", "degree", "kỹ sư", "cử nhân", "master", "phd"]):
                    degree = clean_l
                year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_l)
                if year_match and not year:
                    year = year_match.group(1)

            educations.append(
                Education(
                    institution=inst,
                    degree=degree,
                    year=year,
                )
            )

    if not educations:
        educations = [
            Education(
                institution="University",
                degree="Bachelor's Degree",
            )
        ]

    # 6. Parse Projects
    projects: List[Project] = []
    proj_content = ""
    for sec_name, content in sections.items():
        if any(k in sec_name for k in ["project", "dự án"]):
            proj_content = content
            break

    if proj_content:
        sub_proj = re.split(r"\n###\s+", "\n" + proj_content)
        for entry in sub_proj:
            entry = entry.strip()
            if not entry:
                continue
            proj_lines = [l.strip() for l in entry.splitlines() if l.strip()]
            p_name = proj_lines[0].lstrip("# ").strip()
            bullets = [
                re.sub(r"^[-*•]\s*", "", l)
                for l in proj_lines[1:]
                if l.startswith(("- ", "* ", "• "))
            ]
            projects.append(Project(name=p_name, highlights=bullets))

    # 7. Parse Achievements & Interests
    achievements: List[str] = []
    interests: List[str] = []

    for sec_name, content in sections.items():
        if any(k in sec_name for k in ["certification", "achievement", "giải thưởng", "chứng chỉ"]):
            achievements.extend([
                re.sub(r"^[-*•]\s*", "", l).strip()
                for l in content.splitlines()
                if l.strip() and l.startswith(("- ", "* ", "• "))
            ])
        elif any(k in sec_name for k in ["interest", "sở thích"]):
            # Split by comma or bullets
            for l in content.splitlines():
                clean_l = re.sub(r"^[-*•]\s*", "", l).strip()
                if clean_l:
                    if "," in clean_l:
                        interests.extend([i.strip() for i in clean_l.split(",") if i.strip()])
                    else:
                        interests.append(clean_l)

    return CvInput(
        name=name,
        position=position,
        objective=objective,
        experience=experiences,
        education=educations,
        projects=projects,
        achievements=achievements,
        interests=interests,
    )
