"""Shared, fresh test inputs; no test module imports another test module."""

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "canonical"


def load_canonical_fixture(name: str = "en.v1.json") -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def request_payload(**overrides):
    base = load_canonical_fixture("en.v1.json")["document"]
    payload = {
        "requestId": "req-1",
        "generationId": "generation-1",
        "jobDescription": "Senior Backend Engineer using Python, REST and PostgreSQL.",
        "profile": {
            "name": "Nguyen Van An",
            "email": "an@example.com",
            "phone": "+84 900000000",
            "location": "Ho Chi Minh City",
            "targetPosition": "Backend Engineer",
            "experiences": [{
                "id": "exp-client-1", "company": "Acme", "position": "Backend Engineer",
                "startDate": "2022-01", "endDate": "2025-01",
                "facts": ["Built Python REST APIs serving 10,000 requests per day."],
            }],
            "education": [], "projects": [],
            "skills": [{"id": "skill-1", "name": "Python"}],
            "certifications": [], "achievements": [], "languages": [],
        },
        "options": {"language": "en", "industry": "it_software", "templateSlug": "classic"},
        "renderDefaults": {"design": base["design"], "locale": base["locale"], "settings": base["settings"]},
    }
    for key, value in overrides.items():
        payload[key] = value
    return payload
