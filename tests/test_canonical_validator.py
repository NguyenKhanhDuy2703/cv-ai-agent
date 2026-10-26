import json
from pathlib import Path
import pytest
from src.schemas.canonical_validator import validate_canonical_document, assert_canonical_document, DocumentValidationError

FIXTURES_DIR = Path("d:/Projects/Render/packages/cv-contracts/fixtures")


def load_fixture(name: str):
    path = FIXTURES_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_validate_en_fixture():
    fixture = load_fixture("en.v1.json")
    is_valid, errors = validate_canonical_document(fixture["document"])
    assert is_valid is True, f"Validation failed with errors: {errors}"


def test_validate_vi_fixture():
    fixture = load_fixture("vi.v1.json")
    is_valid, errors = validate_canonical_document(fixture["document"])
    assert is_valid is True, f"Validation failed with errors: {errors}"


def test_validate_wrapped_fixture():
    fixture = load_fixture("en.v1.json")
    is_valid, errors = validate_canonical_document(fixture)
    assert is_valid is True, f"Validation failed with errors: {errors}"


def test_duplicate_entry_id_fails():
    fixture = load_fixture("en.v1.json")
    doc = json.loads(json.dumps(fixture["document"]))
    # Duplicate ID across entries
    first_id = doc["cv"]["sections"][1]["entries"][0]["id"]
    doc["cv"]["sections"][1]["entries"].append(
        {
            "id": first_id,
            "type": doc["cv"]["sections"][1]["entries"][0]["type"],
            "institution": "Dup Univ",
            "area": "CS",
            "degree": "BS",
            "highlights": ["test"],
        }
    )
    is_valid, errors = validate_canonical_document(doc)
    assert is_valid is False
    assert any("Duplicate" in err for err in errors)


def test_mismatched_entry_type_fails():
    fixture = load_fixture("en.v1.json")
    doc = json.loads(json.dumps(fixture["document"]))
    doc["cv"]["sections"][1]["entries"][0]["type"] = "Text"
    is_valid, errors = validate_canonical_document(doc)
    assert is_valid is False
    assert any("Entry type" in err for err in errors)
