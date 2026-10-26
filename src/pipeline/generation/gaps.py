"""Input completeness rules for CV generation."""

import re
from typing import List

from ...schemas.generation import GenerateCvRequest, GenerationGap


_MESSAGES = {
    "en": {
        "jobDescription": ("A job description is required.", "Please provide the target job description."),
        "profile.name": ("Candidate name is required.", "What is your full name?"),
        "profile.email": ("Candidate email is required.", "What email should appear on the CV?"),
        "profile.targetPosition": ("Target position is required.", "Which position are you applying for?"),
        "evidence": ("At least one complete education or fact-backed experience/project is required.", "Please add education details or concrete facts from an experience or project."),
        "profile.phone": ("A phone number is recommended.", "Would you like to add a phone number?"),
        "profile.location": ("A location is recommended.", "Would you like to add your location?"),
        "profile.metrics": ("Verified metrics are recommended for stronger impact.", "Do you have any verified metrics to add?"),
        "profile.dates": ("Dates are recommended for experience and education entries.", "Would you like to add missing dates?"),
    },
    "vi": {
        "jobDescription": ("Cần có mô tả công việc.", "Bạn vui lòng cung cấp JD của vị trí muốn ứng tuyển."),
        "profile.name": ("Cần có họ tên ứng viên.", "Họ và tên đầy đủ của bạn là gì?"),
        "profile.email": ("Cần có email ứng viên.", "Bạn muốn dùng email nào trên CV?"),
        "profile.targetPosition": ("Cần có vị trí mục tiêu.", "Bạn đang ứng tuyển vị trí nào?"),
        "evidence": ("Cần ít nhất một học vấn đầy đủ hoặc kinh nghiệm/dự án có dữ kiện.", "Hãy bổ sung học vấn hoặc dữ kiện cụ thể từ kinh nghiệm hay dự án."),
        "profile.phone": ("Nên bổ sung số điện thoại.", "Bạn có muốn thêm số điện thoại không?"),
        "profile.location": ("Nên bổ sung địa điểm.", "Bạn có muốn thêm địa điểm không?"),
        "profile.metrics": ("Nên bổ sung số liệu đã xác minh để tăng sức thuyết phục.", "Bạn có số liệu đã xác minh nào muốn bổ sung không?"),
        "profile.dates": ("Nên bổ sung thời gian cho kinh nghiệm và học vấn.", "Bạn có muốn bổ sung các mốc thời gian còn thiếu không?"),
    },
}


def detect_gaps(request: GenerateCvRequest) -> List[GenerationGap]:
    lang = request.options.language
    messages = _MESSAGES[lang]
    gaps: List[GenerationGap] = []

    def add(code: str, field: str, severity: str) -> None:
        message, question = messages[field]
        gaps.append(GenerationGap(code=code, field=field, severity=severity, message=message, question=question))

    if not request.job_description.strip():
        add("missing_job_description", "jobDescription", "required")
    if not request.profile.name.strip():
        add("missing_name", "profile.name", "required")
    if not request.profile.email.strip():
        add("missing_email", "profile.email", "required")
    if not request.profile.target_position.strip():
        add("missing_target_position", "profile.targetPosition", "required")

    has_experience = any(any(fact.strip() for fact in item.facts) for item in request.profile.experiences)
    has_project = any(any(fact.strip() for fact in item.facts) for item in request.profile.projects)
    has_education = any(item.institution.strip() and item.degree.strip() for item in request.profile.education)
    if not (has_experience or has_project or has_education):
        add("missing_candidate_evidence", "evidence", "required")

    if not request.profile.phone.strip():
        add("missing_phone", "profile.phone", "recommended")
    if not request.profile.location.strip():
        add("missing_location", "profile.location", "recommended")
    fact_text = " ".join(
        fact
        for item in [*request.profile.experiences, *request.profile.projects]
        for fact in item.facts
    )
    if fact_text and not re.search(r"\d", fact_text):
        add("missing_metrics", "profile.metrics", "recommended")
    dated_items = [*request.profile.experiences, *request.profile.education]
    if dated_items and any(not (item.date or item.start_date or item.end_date) for item in dated_items):
        add("missing_dates", "profile.dates", "recommended")

    return gaps
