
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from ..core.evidence_extractor import METRIC_REGEX, EvidenceStore, COMMON_TECH_TOKENS

BANNED_BUZZWORDS = {
    "rockstar", "ninja", "guru", "wizard", "synergy", "hard-working", "punctual",
    "go-getter", "team player", "detail-oriented", "self-starter", "thought leader",
    "chăm chỉ", "nhiệt huyết", "chịu khó", "ham học hỏi", "hòa đồng", "năng nổ"
}


HALLUCINATED_TECH_COMPANIES = {
    "google", "microsoft", "apple", "amazon", "meta", "facebook", "netflix",
    "openai", "uber", "airbnb", "tesla", "twitter", "bytedance", "oracle",
    "salesforce", "ibm", "spotify", "anthropic"
}


FABRICATED_TITLE_PATTERNS = [
    r"\b(?:as|promoted to|làm|vị trí)\s+(?:senior\s+vice\s+president|vice\s+president|principal\s+architect|chief\s+technology\s+officer|cto|ceo|director|head\s+of\s+engineering|tech\s+lead)\b",
    r"\b(?:senior\s+vice\s+president|vice\s+president|principal\s+architect|chief\s+technology\s+officer|giám\s+đốc\s+kỹ\s+thuật)\b",
]

CERT_KEYWORDS = [
    "aws certified", "gcp certified", "azure certified", "cka", "ckad",
    "pmp", "cissp", "scrum master", "certified kubernetes administrator",
    "chứng chỉ", "certificate", "certification",
]


class GuardResult(BaseModel):
    is_valid: bool
    rejection_reasons: List[str] = Field(default_factory=list)
    checks: Dict[str, bool] = Field(default_factory=dict)


def _extract_numbers_and_metrics(text: str) -> Set[str]:
    """Finds all raw numeric and metric tokens in a text."""
    matches = METRIC_REGEX.findall(text)
    cleaned = set()
    for m in matches:
        s = m.strip().lower()
        if s:
            cleaned.add(s)
            # Also add bare digits if with unit, e.g. "99.9%" -> "99.9"
            digits = re.sub(r"[^\d.]", "", s)
            if digits:
                cleaned.add(digits)
    return cleaned


class DeterministicGuard:
    @staticmethod
    def verify(
        proposed_text: str,
        evidence_ids: List[str],
        original_bullet: str,
        evidence_store: EvidenceStore,
        language: str = "vi",
        current_entry_id: Optional[str] = None,
        entry_dates: Optional[Dict[str, Any]] = None,
    ) -> GuardResult:
        reasons: List[str] = []
        checks: Dict[str, bool] = {}

        clean_proposed = proposed_text.strip()
        lower_proposed = clean_proposed.lower()

        # 1. Evidence ID validity check & cross-entry isolation
        if not evidence_ids:
            reasons.append("Missing evidenceIds: every proposal must link to at least 1 candidate evidence.")
            checks["evidence_id_validity"] = False
        else:
            invalid_ids = [eid for eid in evidence_ids if not evidence_store.get_by_id(eid)]
            if invalid_ids:
                reasons.append(f"Invalid evidence IDs not found in candidate store: {invalid_ids}")
                checks["evidence_id_validity"] = False
            else:
                # Check cross-entry evidence contamination
                cross_entry_violations = []
                for eid in evidence_ids:
                    ev = evidence_store.get_by_id(eid)
                    if ev and ev.entryId and current_entry_id and ev.entryId != current_entry_id:
                        cross_entry_violations.append(f"{eid} (belongs to entry '{ev.entryId}')")
                if cross_entry_violations:
                    reasons.append(
                        f"Cross-entry evidence contamination: cannot cite evidence from other entries for '{current_entry_id}': {cross_entry_violations}"
                    )
                    checks["evidence_id_validity"] = False
                else:
                    checks["evidence_id_validity"] = True

        # 2. Length & format check
        if len(clean_proposed) < 20:
            reasons.append(f"Bullet is too short ({len(clean_proposed)} chars, minimum 20).")
            checks["bullet_length"] = False
        elif len(clean_proposed) > 400:
            reasons.append(f"Bullet is too long ({len(clean_proposed)} chars, maximum 400).")
            checks["bullet_length"] = False
        elif "\n" in clean_proposed:
            reasons.append("Bullet must be a single line without linebreaks.")
            checks["bullet_length"] = False
        else:
            checks["bullet_length"] = True

        # 3. Ban terms check
        found_banned = [term for term in BANNED_BUZZWORDS if term in lower_proposed]
        if found_banned:
            reasons.append(f"Bullet contains banned buzzword/cliché: {found_banned}")
            checks["no_banned_terms"] = False
        else:
            checks["no_banned_terms"] = True

        # 4. 0% Numeric / Metric fabrication check
        proposed_metrics = _extract_numbers_and_metrics(clean_proposed)
        allowed_metrics = set()
        for ev_metric in evidence_store.get_all_metrics():
            allowed_metrics.update(_extract_numbers_and_metrics(ev_metric))
        allowed_metrics.update(_extract_numbers_and_metrics(original_bullet))

        fabricated_metrics = []
        for pm in proposed_metrics:
            if pm.isdigit() and int(pm) <= 1:
                continue
            # 4-digit years (1990-2040) are verified by the date consistency check
            if pm.isdigit() and 1990 <= int(pm) <= 2040:
                continue

            if pm not in allowed_metrics:
                if not any(pm in am or am in pm for am in allowed_metrics):
                    fabricated_metrics.append(pm)

        if fabricated_metrics:
            reasons.append(f"Numeric fabrication detected: ungrounded metrics {fabricated_metrics}")
            checks["metric_fabrication"] = False
        else:
            checks["metric_fabrication"] = True

        # 5. Date consistency check
        proposed_years = set(re.findall(r"\b(19\d\d|20\d\d)\b", clean_proposed))
        orig_years = set(re.findall(r"\b(19\d\d|20\d\d)\b", original_bullet))
        valid_years = set(orig_years)

        if entry_dates:
            for d_val in entry_dates.values():
                if d_val:
                    valid_years.update(re.findall(r"\b(19\d\d|20\d\d)\b", str(d_val)))

            start_str = str(entry_dates.get("start_date") or "")
            end_str = str(entry_dates.get("end_date") or entry_dates.get("date") or "")
            start_m = re.search(r"\b(19\d\d|20\d\d)\b", start_str)
            if start_m:
                s_yr = int(start_m.group(1))
                if any(kw in end_str.lower() for kw in ("present", "hiện tại", "nay")):
                    e_yr = 2026
                else:
                    end_m = re.search(r"\b(19\d\d|20\d\d)\b", end_str)
                    e_yr = int(end_m.group(1)) if end_m else s_yr
                for yr in range(s_yr, e_yr + 1):
                    valid_years.add(str(yr))
        else:
            # Fallback to candidate-wide dates
            for d_item in evidence_store.get_all_dates():
                valid_years.update(re.findall(r"\b(19\d\d|20\d\d)\b", d_item))

        inconsistent_years = [y for y in proposed_years if y not in valid_years]
        if inconsistent_years:
            reasons.append(f"Date inconsistency detected: year(s) {inconsistent_years} not consistent with tenure/evidence.")
            checks["date_consistency"] = False
        else:
            checks["date_consistency"] = True

        # 6. Company & Job Title grounding check
        known_companies = {c.lower() for c in evidence_store.get_all_companies()}
        found_fab_companies = []
        for comp in HALLUCINATED_TECH_COMPANIES:
            if re.search(r"\b" + re.escape(comp) + r"\b", lower_proposed):
                if comp not in known_companies and comp not in original_bullet.lower():
                    found_fab_companies.append(comp)

        at_patterns = re.findall(r"\b(?:at|tại)\s+([A-Z][A-Za-z0-9&]+)\b", clean_proposed)
        for at_comp in at_patterns:
            low = at_comp.lower()
            if (
                low not in known_companies
                and low not in original_bullet.lower()
                and low not in COMMON_TECH_TOKENS
                and low not in {"scale", "scale-up", "high", "runtime", "night", "work", "peak", "least", "most", "time"}
            ):
                found_fab_companies.append(at_comp)

        known_positions = {p.lower() for p in evidence_store.get_all_positions()}
        found_fab_titles = []
        for t_pat in FABRICATED_TITLE_PATTERNS:
            m = re.search(t_pat, lower_proposed)
            if m:
                matched_title = m.group(0).strip()
                if not any(matched_title in kp or kp in matched_title for kp in known_positions) and matched_title not in original_bullet.lower():
                    found_fab_titles.append(matched_title)

        if found_fab_companies or found_fab_titles:
            if found_fab_companies:
                reasons.append(f"Fabricated company detected: {found_fab_companies}")
            if found_fab_titles:
                reasons.append(f"Fabricated job title detected: {found_fab_titles}")
            checks["company_title_grounding"] = False
        else:
            checks["company_title_grounding"] = True

        # 7. Certification grounding check
        all_candidate_text = " ".join([item.value for item in evidence_store.items]).lower() + " " + original_bullet.lower()
        found_fab_certs = []
        for cert in CERT_KEYWORDS:
            if re.search(r"\b" + re.escape(cert) + r"\b", lower_proposed):
                if not re.search(r"\b" + re.escape(cert) + r"\b", all_candidate_text):
                    found_fab_certs.append(cert)

        if found_fab_certs:
            reasons.append(f"Fabricated certification/qualification detected: {found_fab_certs}")
            checks["certification_grounding"] = False
        else:
            checks["certification_grounding"] = True

        # 8. Technology grounding check
        proposed_words = set(re.findall(r"[A-Za-z0-9#+.]+", lower_proposed))
        proposed_techs = proposed_words & COMMON_TECH_TOKENS

        known_techs = {t.lower() for t in evidence_store.get_all_technologies()}
        orig_techs = set(re.findall(r"[A-Za-z0-9#+.]+", original_bullet.lower())) & COMMON_TECH_TOKENS
        known_techs.update(orig_techs)

        linked_ev_texts = " ".join([evidence_store.get_by_id(eid).value for eid in evidence_ids if evidence_store.get_by_id(eid)]).lower()
        linked_techs = set(re.findall(r"[A-Za-z0-9#+.]+", linked_ev_texts)) & COMMON_TECH_TOKENS
        known_techs.update(linked_techs)

        fabricated_techs = [tech for tech in proposed_techs if tech not in known_techs]
        if fabricated_techs:
            reasons.append(f"Fabricated skills/technologies not in candidate background: {fabricated_techs}")
            checks["skill_grounding"] = False
        else:
            checks["skill_grounding"] = True

        is_valid = len(reasons) == 0
        return GuardResult(
            is_valid=is_valid,
            rejection_reasons=reasons,
            checks=checks,
        )
