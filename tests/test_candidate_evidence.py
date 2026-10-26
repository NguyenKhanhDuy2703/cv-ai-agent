"""Evidence must come from the generation profile, not an existing CV."""

from src.pipeline.generation.evidence import build_candidate_evidence


def test_candidate_facts_are_traceable_and_complete(candidate_profile):
    store = build_candidate_evidence(candidate_profile)
    assert {item.value for item in store.get_by_category("company")} == {"Acme"}
    assert {item.value for item in store.get_by_category("position")} == {"Backend Engineer"}
    assert store.get_by_category("date")
    assert store.get_by_category("metric")
    assert "python" in store.get_all_technologies()
    assert store.get_by_category("highlight")[0].value == candidate_profile.experiences[0].facts[0]
    for item in store.items:
        assert item.id.startswith("ev-")
        assert item.sourcePath.startswith("profile.")
        assert item.normalizedValue == item.value.strip().lower()
        assert store.get_by_id(item.id) == item


def test_evidence_ids_remain_stable_for_the_same_profile(candidate_profile):
    first = build_candidate_evidence(candidate_profile)
    second = build_candidate_evidence(candidate_profile)
    assert first.model_dump() == second.model_dump()


def test_duplicate_facts_do_not_duplicate_evidence(candidate_profile):
    original = candidate_profile.experiences[0].facts[0]
    candidate_profile.experiences[0].facts.append(original)
    store = build_candidate_evidence(candidate_profile)
    assert len({item.id for item in store.items}) == len(store.items)
    assert [item.value for item in store.get_by_category("highlight")].count(original) == 1
