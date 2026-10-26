"""
Tests for the new CvInput schema.
These run against src/schemas/cv_input.py which replaces the old CoreCvInput.
"""
import pytest
from pydantic import ValidationError


class TestCvInputSchema:
    def _minimal_valid(self) -> dict:
        """Minimal payload that satisfies all required fields."""
        return {
            "name": "Nguyen Van A",
            "position": "Senior Backend Engineer",
            "objective": "5 years of backend experience seeking senior role.",
            "experience": [
                {
                    "company": "FPT Software",
                    "title": "Backend Engineer",
                    "start": "2021-01",
                    "highlights": ["Built microservice handling 10k req/s"],
                }
            ],
            "education": [
                {
                    "institution": "Hanoi University of Technology",
                    "degree": "B.Eng. Computer Science",
                }
            ],
        }

    def test_minimal_valid_input_parses(self):
        from src.schemas.cv_input import CvInput
        cv = CvInput(**self._minimal_valid())
        assert cv.name == "Nguyen Van A"
        assert cv.position == "Senior Backend Engineer"
        assert len(cv.experience) == 1
        assert len(cv.education) == 1

    def test_optional_fields_default_to_empty(self):
        from src.schemas.cv_input import CvInput
        cv = CvInput(**self._minimal_valid())
        assert cv.projects == []
        assert cv.achievements == []
        assert cv.interests == []
        assert cv.bonus is None
        assert cv.jd is None

    def test_missing_name_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        del data["name"]
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "name" in str(exc_info.value)

    def test_missing_position_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        del data["position"]
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "position" in str(exc_info.value)

    def test_missing_objective_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        del data["objective"]
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "objective" in str(exc_info.value)

    def test_empty_experience_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data["experience"] = []
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "experience" in str(exc_info.value)

    def test_experience_missing_highlights_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data["experience"][0]["highlights"] = []
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "highlights" in str(exc_info.value)

    def test_empty_education_raises(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data["education"] = []
        with pytest.raises(ValidationError) as exc_info:
            CvInput(**data)
        assert "education" in str(exc_info.value)

    def test_full_input_with_all_optional_fields(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data.update({
            "projects": [
                {
                    "name": "CV AI Agent",
                    "url": "https://github.com/example/cv-ai",
                    "tech": ["Python", "FastAPI"],
                    "highlights": ["Built YAML-in YAML-out pipeline"],
                }
            ],
            "achievements": ["Google Cloud Professional Certified", "Hackathon 2022 Winner"],
            "interests": ["Open Source", "Running"],
            "bonus": {
                "notes": [
                    {"text": "Led a team of 8 people on FPT project, not yet written in highlights"},
                    {"attach_to": "experience[0]", "text": "Also familiar with Kubernetes"},
                ],
                "directives": ["Emphasise backend experience, do not mention frontend"],
                "references": ["https://linkedin.com/in/example"],
            },
            "jd": "We are looking for a Senior Backend Engineer with 3+ years Python experience...",
            "control": {
                "locale": "en",
                "locked": ["education"],
            },
        })
        cv = CvInput(**data)
        assert len(cv.projects) == 1
        assert cv.projects[0].name == "CV AI Agent"
        assert len(cv.achievements) == 2
        assert cv.bonus is not None
        assert len(cv.bonus.notes) == 2
        assert cv.jd is not None
        assert cv.control.locale == "en"
        assert "education" in cv.control.locked

    def test_experience_end_date_present(self):
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data["experience"][0]["end"] = "2024-06"
        cv = CvInput(**data)
        assert cv.experience[0].end == "2024-06"

    def test_experience_no_end_date_means_present(self):
        from src.schemas.cv_input import CvInput
        cv = CvInput(**self._minimal_valid())
        assert cv.experience[0].end is None  # None = current/present

    def test_yaml_and_markdown_input_notes(self):
        """Bonus notes can be plain text (the user may paste raw notes)."""
        from src.schemas.cv_input import CvInput
        data = self._minimal_valid()
        data["bonus"] = {
            "notes": [{"text": "Raw markdown note **bold**"}],
        }
        cv = CvInput(**data)
        assert cv.bonus.notes[0].text == "Raw markdown note **bold**"
