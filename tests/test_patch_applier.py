import json
from pathlib import Path
import pytest

from src.schemas.canonical_dto import SemanticPatch, compute_bullet_hash
from src.schemas.patch_applier import apply_semantic_patch, apply_semantic_patches, PatchConflictError
from src.schemas.canonical_validator import validate_canonical_document

FIXTURES_DIR = Path("d:/Projects/Render/packages/cv-contracts/fixtures")


@pytest.fixture
def en_fixture():
    path = FIXTURES_DIR / "en.v1.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["document"]


@pytest.fixture
def vi_fixture():
    path = FIXTURES_DIR / "vi.v1.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["document"]


def find_first_experience_bullet(doc):
    for sec in doc["cv"]["sections"]:
        if sec["entryType"] == "Experience":
            for ent in sec["entries"]:
                if ent["highlights"]:
                    return sec["id"], ent["id"], 0, ent["highlights"][0]
    raise ValueError("No Experience bullet found in fixture")


def test_apply_patch_happy_path(en_fixture):
    sec_id, ent_id, idx, original_bullet = find_first_experience_bullet(en_fixture)
    original_hash = compute_bullet_hash(original_bullet)

    new_value = "Spearheaded cloud architecture migration using Kubernetes and AWS ECS, boosting reliability to 99.99%."
    patch = SemanticPatch(
        sectionId=sec_id,
        entryId=ent_id,
        index=idx,
        beforeHash=original_hash,
        value=new_value,
        evidenceIds=["ev-1"],
    )

    updated_doc = apply_semantic_patch(en_fixture, patch)

    # Verify bullet changed
    for sec in updated_doc["cv"]["sections"]:
        if sec["id"] == sec_id:
            for ent in sec["entries"]:
                if ent["id"] == ent_id:
                    assert ent["highlights"][idx] == new_value

    # Verify document is still valid
    is_valid, errors = validate_canonical_document(updated_doc)
    assert is_valid is True, f"Validation failed: {errors}"

    # Verify non-destructive: design, locale, settings are untouched
    assert updated_doc["design"] == en_fixture["design"]
    assert updated_doc["locale"] == en_fixture["locale"]
    assert updated_doc["settings"] == en_fixture["settings"]


def test_hash_mismatch_rejected(en_fixture):
    sec_id, ent_id, idx, original_bullet = find_first_experience_bullet(en_fixture)
    wrong_hash = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

    patch = SemanticPatch(
        sectionId=sec_id,
        entryId=ent_id,
        index=idx,
        beforeHash=wrong_hash,
        value="New bullet text",
    )

    updated_doc, errors = apply_semantic_patches(en_fixture, [patch])
    assert len(errors) > 0
    assert "beforeHash mismatch" in errors[0]
    # Document unchanged
    assert updated_doc == en_fixture


def test_locked_path_rejected(en_fixture):
    sec_id, ent_id, idx, original_bullet = find_first_experience_bullet(en_fixture)
    original_hash = compute_bullet_hash(original_bullet)

    patch = SemanticPatch(
        sectionId=sec_id,
        entryId=ent_id,
        index=idx,
        beforeHash=original_hash,
        value="New bullet text",
    )

    # Lock this entry
    updated_doc, errors = apply_semantic_patches(
        en_fixture,
        [patch],
        locked_paths=[ent_id],
    )
    assert len(errors) > 0
    assert "locked" in errors[0]
    assert updated_doc == en_fixture


def test_occ_base_version_conflict_rejected(en_fixture):
    sec_id, ent_id, idx, original_bullet = find_first_experience_bullet(en_fixture)
    original_hash = compute_bullet_hash(original_bullet)

    patch = SemanticPatch(
        sectionId=sec_id,
        entryId=ent_id,
        index=idx,
        beforeHash=original_hash,
        value="New bullet text",
    )

    # Base version mismatch
    updated_doc, errors = apply_semantic_patches(
        en_fixture,
        [patch],
        expected_base_version=12,
        current_base_version=13,
    )
    assert len(errors) > 0
    assert "Optimistic lock conflict" in errors[0]
    assert updated_doc == en_fixture


def test_non_experience_entry_rejected(en_fixture):
    # Find an Education section
    edu_sec = next(s for s in en_fixture["cv"]["sections"] if s["entryType"] == "Education")
    edu_ent = edu_sec["entries"][0]

    patch = SemanticPatch(
        sectionId=edu_sec["id"],
        entryId=edu_ent["id"],
        index=0,
        beforeHash="anyhash",
        value="New bullet",
    )

    updated_doc, errors = apply_semantic_patches(en_fixture, [patch])
    assert len(errors) > 0
    assert "only Experience is allowed" in errors[0]
