"""
Deterministic Semantic Patch Applier for RenderCV Canonical Documents.

Guarantees:
- Targets elements only by stable sectionId & entryId.
- Only modifies Experience.highlights[index].
- Enforces beforeHash matching (atomic optimistic lock per bullet).
- Respects locked paths.
- Re-validates document against canonical JSON Schema & invariants after apply.
- Purely non-destructive: design, locale, settings and unrelated entries are never mutated.
"""
import copy
from typing import Any, Dict, List, Optional, Set, Tuple

from .canonical_dto import SemanticPatch, compute_bullet_hash
from .canonical_validator import validate_canonical_document, DocumentValidationError


class PatchConflictError(ValueError):
    """Raised when patch conflict occurs (hash mismatch, version mismatch, or locked path)."""


class PatchTargetNotFoundError(KeyError):
    """Raised when sectionId or entryId cannot be found."""


def is_entry_or_section_locked(section_id: str, entry_id: str, locked_paths: List[str]) -> bool:
    """Checks if the entire section or entry is locked, ignoring highlight-level paths."""
    if not locked_paths:
        return False
    locked_set = set(locked_paths)
    candidates = {
        section_id,
        entry_id,
        f"{section_id}.{entry_id}",
        f"{section_id}/{entry_id}",
        f"{section_id}.{entry_id}.highlights",
        f"sections.{section_id}",
        f"entries.{entry_id}",
    }
    return bool(candidates & locked_set)


def is_path_locked(section_id: str, entry_id: str, index: int, locked_paths: List[str]) -> bool:
    """Checks if a target highlight is within any declared locked path."""
    if not locked_paths:
        return False
    locked_set = set(locked_paths)
    candidates = {
        section_id,
        entry_id,
        f"{section_id}.{entry_id}",
        f"{section_id}/{entry_id}",
        f"{section_id}.{entry_id}.highlights",
        f"{section_id}.{entry_id}.highlights[{index}]",
        f"{entry_id}.highlights[{index}]",
        f"sections.{section_id}",
        f"entries.{entry_id}",
    }
    return bool(candidates & locked_set)


def apply_semantic_patch(
    document: Dict[str, Any],
    patch: SemanticPatch,
    locked_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Applies a single semantic patch to a RenderCV document.
    Returns the new updated document copy.
    Raises PatchConflictError or PatchTargetNotFoundError on failure.
    """
    updated_doc, errors = apply_semantic_patches(
        document=document,
        patches=[patch],
        locked_paths=locked_paths,
    )
    if errors:
        raise PatchConflictError("; ".join(errors))
    return updated_doc


def apply_semantic_patches(
    document: Dict[str, Any],
    patches: List[SemanticPatch],
    locked_paths: Optional[List[str]] = None,
    expected_base_version: Optional[int] = None,
    current_base_version: Optional[int] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Atomically applies a sequence of semantic patches to a RenderCV document.
    If any patch fails or document becomes invalid, returns (original_doc, [error_reasons]).
    """
    errors: List[str] = []

    # 1. Check base version OCC
    if expected_base_version is not None and current_base_version is not None:
        if expected_base_version != current_base_version:
            return document, [
                f"Optimistic lock conflict: expected baseVersion {expected_base_version}, but current is {current_base_version}"
            ]

    if not patches:
        return copy.deepcopy(document), []

    locked_paths = locked_paths or []
    new_doc = copy.deepcopy(document)

    # Unwrap if wrapped
    target = new_doc.get("document", new_doc)
    cv = target.get("cv", {})
    sections = cv.get("sections", [])

    # Index sections by id
    section_map = {sec.get("id"): sec for sec in sections if isinstance(sec, dict)}

    for p_idx, patch in enumerate(patches):
        sec_id = patch.sectionId
        ent_id = patch.entryId

        # Check locked paths
        if is_path_locked(sec_id, ent_id, patch.index, locked_paths):
            errors.append(f"Patch {p_idx} target '{sec_id}/{ent_id}' is locked.")
            continue

        sec = section_map.get(sec_id)
        if not sec:
            errors.append(f"Patch {p_idx}: Section with id '{sec_id}' not found.")
            continue

        if sec.get("entryType") != "Experience":
            errors.append(
                f"Patch {p_idx}: Section '{sec_id}' entryType is '{sec.get('entryType')}', only Experience is allowed in MVP."
            )
            continue

        # Find entry
        entries = sec.get("entries", [])
        entry = next((e for e in entries if isinstance(e, dict) and e.get("id") == ent_id), None)
        if not entry:
            errors.append(f"Patch {p_idx}: Entry with id '{ent_id}' not found in section '{sec_id}'.")
            continue

        if entry.get("type") != "Experience":
            errors.append(
                f"Patch {p_idx}: Entry '{ent_id}' type is '{entry.get('type')}', expected Experience."
            )
            continue

        highlights = entry.get("highlights")
        if not isinstance(highlights, list):
            errors.append(f"Patch {p_idx}: Entry '{ent_id}' has no highlights list.")
            continue

        if patch.index < 0 or patch.index >= len(highlights):
            errors.append(
                f"Patch {p_idx}: Highlight index {patch.index} out of bounds (length: {len(highlights)})."
            )
            continue

        # Check beforeHash
        current_bullet = highlights[patch.index]
        actual_hash = compute_bullet_hash(current_bullet)
        if actual_hash != patch.beforeHash:
            errors.append(
                f"Patch {p_idx}: beforeHash mismatch for bullet {patch.index} in entry '{ent_id}'. "
                f"Expected '{patch.beforeHash}', found '{actual_hash}'."
            )
            continue

        # Apply mutation
        highlights[patch.index] = patch.value

    if errors:
        return document, errors

    # Validate resulting document
    is_valid, validation_errors = validate_canonical_document(new_doc)
    if not is_valid:
        return document, [f"Applied document failed canonical schema validation: {'; '.join(validation_errors[:3])}"]

    return new_doc, []
