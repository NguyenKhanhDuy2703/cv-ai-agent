"""
Canonical RenderCV Document Validator in Python.
Uses the exported JSON Schema from @rendercv/cv-contracts plus runtime invariant checks:
- Standard JSON schema structural validation
- Section entry type matching (entry.type == section.entryType)
- Stable ID uniqueness across sections, entries, social networks, custom connections
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import jsonschema
from jsonschema.exceptions import ValidationError

_SCHEMA_PATH = Path(__file__).parent / "render_cv_schema.json"
_SCHEMA: Dict[str, Any] = {}
_VALIDATOR: jsonschema.Draft202012Validator = None


def _get_validator() -> jsonschema.Draft202012Validator:
    global _SCHEMA, _VALIDATOR
    if _VALIDATOR is None:
        if not _SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Render CV JSON Schema not found at {_SCHEMA_PATH}")
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _SCHEMA = json.load(f)
        # Use Draft202012Validator or Draft7Validator depending on schema meta
        _VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)
    return _VALIDATOR


class DocumentValidationError(ValueError):
    """Raised when a canonical Render document fails schema or semantic validation."""

    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or [message]


def validate_canonical_document(doc: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a RenderCV canonical document (the dict containing 'cv', 'design', 'locale', 'settings').
    Returns (is_valid, list_of_error_strings).
    """
    errors: List[str] = []

    if not isinstance(doc, dict):
        return False, ["Canonical document must be a JSON object (dict)"]

    # If wrapped in envelope {"document": {...}}, extract document
    target_doc = doc.get("document", doc) if "document" in doc and "cv" not in doc else doc

    # 1. Structural validation via JSON Schema
    try:
        validator = _get_validator()
        for error in validator.iter_errors(target_doc):
            path_str = ".".join(str(p) for p in error.absolute_path) or "root"
            errors.append(f"[{path_str}] {error.message}")
    except Exception as exc:
        errors.append(f"JSON Schema validation failure: {exc}")

    # 2. Semantic invariants from Render contract
    cv = target_doc.get("cv", {})
    if isinstance(cv, dict):
        ids = set()

        def register_id(id_val: Any, loc: str):
            if not id_val or not isinstance(id_val, str):
                errors.append(f"[{loc}] Missing or empty stable ID")
                return
            if id_val in ids:
                errors.append(f"[{loc}] Duplicate stable ID '{id_val}'")
            ids.add(id_val)

        for i, item in enumerate(cv.get("social_networks", []) or []):
            if isinstance(item, dict) and "id" in item:
                register_id(item["id"], f"cv.social_networks[{i}].id")

        for i, item in enumerate(cv.get("custom_connections", []) or []):
            if isinstance(item, dict) and "id" in item:
                register_id(item["id"], f"cv.custom_connections[{i}].id")

        for i, section in enumerate(cv.get("sections", []) or []):
            if not isinstance(section, dict):
                continue
            sec_id = section.get("id")
            sec_type = section.get("entryType")
            register_id(sec_id, f"cv.sections[{i}].id")

            sec_entry_ids = set()
            for j, entry in enumerate(section.get("entries", []) or []):
                if not isinstance(entry, dict):
                    continue
                ent_id = entry.get("id")
                ent_type = entry.get("type")

                if ent_type != sec_type:
                    errors.append(
                        f"[cv.sections[{i}].entries[{j}]] Entry type '{ent_type}' does not match section entryType '{sec_type}'"
                    )

                if ent_id in sec_entry_ids:
                    errors.append(
                        f"[cv.sections[{i}].entries[{j}]] Duplicate entry ID '{ent_id}' in section '{sec_id}'"
                    )
                sec_entry_ids.add(ent_id)
                register_id(ent_id, f"cv.sections[{i}].entries[{j}].id")

    return (len(errors) == 0, errors)


def assert_canonical_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Validates document and returns it if valid, raises DocumentValidationError if not."""
    is_valid, errors = validate_canonical_document(doc)
    if not is_valid:
        raise DocumentValidationError(f"Invalid canonical document: {'; '.join(errors[:5])}", errors=errors)
    return doc.get("document", doc) if "document" in doc and "cv" not in doc else doc
