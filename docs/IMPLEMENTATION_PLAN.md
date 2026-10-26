# Implementation Plan: CV Tailor Agent

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-10-12 |
| **Based on** | `proposal.md` v0.2, `PLAN.md` v0.1, `AGENT_RUNBOOK.md` v0.1 |
| **Stack** | Python 3.13, FastAPI, Pydantic v2, ruamel.yaml, pytest |
| **Strategy** | Inside-out: schemas → YAML layer → LLM layer → pipeline → API |

---

## Project Summary

**CV Tailor Agent** is a YAML-in → YAML-out pipeline that:
1. Takes a structured CV (`core`), optional bonus info (`bonus`), and run control (`control`) as YAML input.
2. Rewrites experience bullets in STAR format using an LLM — without fabricating any facts.
3. Outputs a clean `cv.yaml` and a `report.yaml` detailing every change, used/unused bonus notes, conflicts, and JD keyword coverage.

**Key constraints:**
- No hallucination: every number, name, and metric in the output must be traceable to the input.
- No storing CV content (stateless, privacy-first).
- LLM is only called for language tasks; all structural work is done in pure Python.
- The pipeline must work without an LLM API key (mock provider for all tests).

---

## Technology Stack

| Layer | Tool |
|---|---|
| Runtime | Python 3.13 (≥3.11 required) |
| Schema & Validation | Pydantic v2 |
| YAML I/O | ruamel.yaml (preserves comments, key order) |
| Web API | FastAPI + Uvicorn + sse-starlette |
| LLM Clients | google-genai, openai (optional; mock for tests) |
| Retry / Timeout | tenacity |
| Config | pydantic-settings |
| Testing | pytest + pytest-asyncio |

---

## Current State Assessment

The repo has a skeleton with:
- `src/schemas/` — partial schemas (`cv.py`, `context.py`, `events.py`, `proposal.py`)
- `src/core/` — `AIModelClient` protocol + `CoreAIClient` stub (simulates JD analysis + experience generation)
- `src/guard/anti_hallucination.py` — basic numeric fact-checker (regex-based)
- `src/industry/context.py` — `get_industry_context()` placeholder returning empty string
- `src/pipeline/orchestrator.py` — `CvTailorPipeline` with stub MVP steps (no real YAML layer, no LLM integration)
- `src/api/` — FastAPI server with SSE stream-generate route + health check
- `tests/` — 5 passing baseline tests

**Gap vs. documented plan (PLAN.md epics):**

| Epic | Status | Gap |
|---|---|---|
| E0 – Foundation | ✅ Done (partial) | Missing: lint config, strict type check, CI, test script aliases |
| E1 – Data contracts | 🟡 Partial | `Leaf`, `Fragment`, `Constraint`, `RewriteResult` absent; size limits missing |
| E2 – YAML layer | ❌ Missing | No `collectLeaves()`, `patch()`, locked-path enforcement, round-trip tests |
| E3 – LLM layer | 🟡 Partial | Protocol + stub exist; no mock provider, no retry/timeout/budget, no prompts |
| E4 – Input normalisation | 🟡 Partial | Bonus normalisation stub; no Fragment extraction, no Constraint parsing |
| E5 – Guard | 🟡 Partial | Numeric check only; missing named-entity check, ban_terms, source_ids |
| E6 – Rewrite | ❌ Missing | No rewrite step, no parallel execution, no retry loop, no fallback |
| E7 – JD analysis | ❌ Missing | No JD keyword extraction, no relevance scoring |
| E8 – Conflict detection | ❌ Missing | Stub keyword scan only |
| E9 – Report & export | 🟡 Partial | `CvReport` schema exists; no YAML serialisation of output |
| E10 – Industry slot | ✅ Done | `get_industry_context()` returns empty (correct MVP behaviour) |
| E11 – Public API | 🟡 Partial | Basic SSE route exists; missing `/v1/tailor`, auth, rate-limit, PII masking |
| E12 – Evaluation | ❌ Missing | No golden fixtures, no evaluation script |

---

## Milestones

```
M1 — Offline framework (no LLM): YAML round-trip, schemas, YAML layer
M2 — MVP rewrite (CLI):           LLM layer + mock, Guard, pipeline, report, CLI
M3 — JD targeting:                JD analysis, selection, conflict detection
M4 — Public service:              API hardening, auth, SSE, PII, security
M5 — Quality & ops:               Evaluation, container, docs
```

---

## Task Dependency Graph

```
T01 → T02 → T03 ──┬─► T06 ──► T08 ──► T09 → T10 → T12 → T13
                   │                    ▲               │
       T04 ─────── ┴──────────── T07 ───┘               ▼
       T05 ──────────────────────────────► T10        T14
       T11 (industry slot) ──► T10                    T15
```

---

## Tasks

---

### T01 — Internal data contracts: Leaf, Fragment, Constraint, RewriteResult

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M1 |
| **Dependencies** | None |
| **Epic refs** | E1-4 |

**Objective:** Define the four internal types that the pipeline passes between steps.

**Types to add to `src/schemas/internal.py`:**
- `Leaf` — `{path: str, text: str, locked: bool}`
- `Fragment` — `{id: str, text: str, attach_to: str | None, target: str | None, unplaced: bool}`
- `Constraint` — `{ban_terms: list[str], emphasize: list[str], tone: str | None, raw: str}`
- `RewriteResult` — `{path: str, text: str, source_ids: list[str]}`

**Files affected:** `src/schemas/internal.py` (new)

**Tests:** `tests/test_internal_schemas.py` — instantiate each type, verify defaults and validation.

**Acceptance criteria:**
- All four types instantiate with minimal required fields.
- Invalid inputs raise `ValidationError`.

---

### T02 — Standardised error format

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M1 |
| **Dependencies** | T01 |
| **Epic refs** | E1-8 |

**Objective:** Define `AgentError(code, path, hint)` — used throughout the pipeline and API.

**Files affected:** `src/schemas/errors.py` (new), minor update to `src/pipeline/orchestrator.py`

**Acceptance criteria:**
- `AgentError` carries `code`, `path`, `hint`.
- `step1_validate_core` raises `AgentError(code="CORE_INVALID")` not bare `ValueError`.

---

### T03 — Input size limits

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M1 |
| **Dependencies** | T02 |
| **Epic refs** | E1-6 |

**Objective:** Enforce hard input limits (YAML length, entry count, note count). Raise `AgentError(code="INPUT_TOO_LARGE")`.

**Files affected:** `src/schemas/validators.py` (new), called from pipeline step 1

**Acceptance criteria:** Each limit triggers the correct error; valid inputs pass.

---

### T04 — YAML layer: parse, collectLeaves, patch, serialize

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M1 |
| **Dependencies** | T01 |
| **Epic refs** | E2-1 through E2-7 |

**Objective:** Build the ruamel.yaml I/O layer used by the pipeline.

**Functions in `src/yaml_layer/io.py`:**
- `parse_yaml(text) → CommentedMap` — error includes line/column
- `collect_leaves(doc, locked) → list[Leaf]` — stable paths, skips locked
- `patch(doc, path, text) → None` — in-place, preserves comments
- `strip_control_bonus(doc) → CommentedMap`
- `serialize(doc) → str`

**Files affected:** `src/yaml_layer/__init__.py`, `src/yaml_layer/io.py` (both new)

**Tests:** `tests/test_yaml_layer.py` — bad YAML, stable paths, single-line patch diff, locked exclusion, strip, re-parse.

**Acceptance criteria:** Comments and key order preserved; all tests pass.

---

### T05 — Round-trip golden tests (GATE M1)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M1 |
| **Dependencies** | T04 |
| **Epic refs** | E2-8 |

**Objective:** 10 YAML fixtures (unknown keys, comments, Vietnamese Unicode, locked sections, empty sections). `serialize(parse_yaml(text)) == text` for 3 consecutive runs.

**Files affected:** `tests/golden/fixture_01.yaml` … `tests/golden/fixture_10.yaml`, `tests/test_round_trip.py`

**Acceptance criteria (GATE M1):** All 10 fixtures pass; single-leaf patch changes exactly one line; output validates against `CoreCvInput`.

---

### T06 — LLM layer: provider interface + mock provider

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T01 |
| **Epic refs** | E3-1, E3-5 |

**Objective:** `LLMProvider` protocol with `generate_structured`; `MockProvider` returning configured responses. All tests use mock.

**Files affected:** `src/llm/base.py`, `src/llm/mock_provider.py`, `src/llm/__init__.py` (all new)

**Acceptance criteria:** Mock returns valid typed response; interface hides provider details.

---

### T07 — Prompt templates

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T06 |
| **Epic refs** | E3-9 |

**Objective:** Versioned `.md` prompt templates; `PromptLoader` fills variables and wraps user data in `<USER_DATA>` boundaries.

**Files affected:** `prompts/rewrite.v1.md`, `src/llm/prompt_loader.py` (both new)

**Acceptance criteria:** Template renders correctly; user data is boundary-wrapped; missing variable raises `AgentError`.

---

### T08 — Retry, timeout, budget enforcement

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T06 |
| **Epic refs** | E3-6, E3-7, E3-8 |

**Objective:** Wrap LLM calls with tenacity retry, per-call timeout, token budget, and schema-error retry.

**Files affected:** `src/llm/base.py` (update), `src/llm/retry.py` (new)

**Acceptance criteria:** All four error scenarios tested with mock; no real LLM calls in tests.

---

### T09 — Fragment extraction and Constraint parsing

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T04, T06 |
| **Epic refs** | E4-1 through E4-5, E4-7 |

**Objective:** Pipeline steps ① (all-at-once validation) and ② (bonus normalisation into Fragments and Constraints).

**Files affected:** `src/pipeline/steps/step1_validate.py`, `src/pipeline/steps/step2_normalize_bonus.py` (both new), `src/pipeline/orchestrator.py` (update)

**Acceptance criteria:** One pass reports all errors; 3-idea note → 3 fragments; directive → Constraint via mock; unrecognised → `unparsed_directives`.

---

### T10 — Guard: complete anti-hallucination rules

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T04, T09 |
| **Epic refs** | E5-1 through E5-9 |

**Objective:** Extend Guard with evidence corpus, named-entity rule, ban_terms rule, locale rule, source_ids rule, length rule. Mutation test: ≥ 95% of 50 fabricated bullets rejected.

**Files affected:** `src/guard/anti_hallucination.py` (extend), `src/guard/evidence.py` (new)

**Acceptance criteria:** Mutation test ≥ 95%; all rule unit tests pass.

---

### T11 — Industry context slot (tests + docs)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T10 |
| **Epic refs** | E10-1, E10-2, E10-3 |

**Objective:** Tests confirming slot returns empty by default and that injecting dummy pack changes whitelist without touching core code. Document pack format.

**Files affected:** `tests/test_industry.py` (new), `docs/industry-pack.md` (new), minor update to `src/industry/context.py`

**Acceptance criteria:** Tests pass; pack format is documented.

---

### T12 — Rewrite step + full pipeline + CLI (GATE M2)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M2 |
| **Dependencies** | T09, T10 |
| **Epic refs** | E6-1 through E6-9, E9-1 through E9-7 |

**Objective:** Full MVP pipeline: rewrite (parallel, concurrency=3), Guard loop (max 2 retries, fallback to original), export (cv.yaml + report.yaml), CLI entry point.

**Files affected:** `src/pipeline/steps/step7_rewrite.py`, `src/pipeline/steps/step9_export.py`, `src/pipeline/orchestrator.py`, `src/cli.py` (new or updated)

**E2E test:** CLI on fixture → valid output; two mock runs → identical output.

**Acceptance criteria (GATE M2):** E2E passes; bullet count preserved; locked paths unchanged; fallback works; output validates.

---

### T13 — JD analysis, selection, conflict detection (GATE M3)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M3 |
| **Dependencies** | T12 |
| **Epic refs** | E7-1 through E7-7, E8-1 through E8-4, E4-6, E9-4 |

**Objective:** Steps ⑤⑥④ + ATS score.

**Files affected:** `src/pipeline/steps/step4_conflicts.py`, `src/pipeline/steps/step5_jd_analysis.py`, `src/pipeline/steps/step6_select.py`, `prompts/jd-analyze.v1.md` (all new)

**Acceptance criteria (GATE M3):** Two JDs → two distinct outputs; JD-only keywords in `missing`; conflict flagged; ATS score deterministic.

---

### T14 — API hardening, auth, rate-limit, PII, SSE (GATE M4)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M4 |
| **Dependencies** | T12 |
| **Epic refs** | E11-1 through E11-10 |

**Objective:** `POST /v1/tailor`, body size limit, API key auth, rate limiting, SSE events, cancel on disconnect, PII masking, prompt injection protection.

**Files affected:** `src/api/routes.py` (extend), `src/api/middleware.py`, `src/api/auth.py` (new)

**Acceptance criteria (GATE M4):** Security tests pass; no PII in logs; SSE order correct; disconnect cancels calls.

---

### T15 — Evaluation fixtures, golden tests, operations docs (GATE M5)

| Field | Value |
|---|---|
| **Status** | `TODO` |
| **Milestone** | M5 |
| **Dependencies** | T12, T13 |
| **Epic refs** | E12-1 through E12-6, E13-1 through E13-5, E14-1 through E14-4 |

**Objective:** 10 CV + 10 JD eval fixtures, evaluation script, Docker container, structured logging, alerts, documentation.

**Files affected:** `tests/eval/`, `scripts/eval.py`, `Dockerfile`, `docs/contract.md`, `docs/api.md`, `docs/operations.md` (all new)

**Acceptance criteria (GATE M5):** All tests pass; container builds; docs have working examples; LIVE_PENDING items listed.

---

## Implementation Order

| # | Task | Milestone | Status |
|---|---|---|---|
| T01 | Internal data contracts (Leaf, Fragment, Constraint, JDProfile) | M1 | `DONE` |
| T02 | Standardised error format (LLMError hierarchy) | M1 | `DONE` |
| T03 | Input size limits | M1 | `TODO` |
| T04 | YAML layer (ruamel.yaml parse, serialize, load) | M1 | `DONE` |
| T05 | Round-trip golden tests (GATE M1) | M1 | `DONE` |
| T06 | LLM layer: interface + mock + GeminiProvider | M2 | `DONE` |
| T07 | Prompt templates (STAR rewrite, JD analysis) | M2 | `DONE` |
| T08 | Retry, timeout, bounded backoff, error classification | M2 | `DONE` |
| T09 | Fragment extraction + Constraint parsing | M2 | `DONE` |
| T10 | Guard: anti-hallucination verification (metrics, ban_terms) | M2 | `DONE` |
| T11 | Industry context slot (tests + docs) | M2 | `DONE` |
| T12 | Rewrite step + full pipeline (GATE M2) | M2 | `DONE` |
| T13 | JD analysis, selection, keyword match score | M3 | `DONE` |
| T14 | API tailoring endpoint (POST /v1/ai/tailor) | M4 | `DONE` |
| T15 | Evaluation, ops, docs (GATE M5) | M5 | `TODO` |


---

## Risks

| Risk | Mitigation |
|---|---|
| Guard too strict — rejects valid Vietnamese text | T10: normalise accents; tune with mutation test |
| LLM schema non-compliance | T08: retry once, fail gracefully |
| YAML comment/order loss | T05: golden round-trip tests |
| Prompt injection via Bonus/JD | T07: boundary markers; T10: Guard rejects out-of-scope |
| Cost overrun | T08: token budget; T14: rate limiting |
| PII in logs | T14: log middleware masks email/phone |

---

## Open Decisions (defaults applied)

| # | Decision | Default |
|---|---|---|
| D1 | Quality criteria | Zero fabricated metrics; keyword coverage ≥ 60% on eval set |
| D2 | JD required? | No; no-JD mode runs style normalisation only |
| D3 | User sees report? | Yes, returned alongside cv |
| D4 | Cost/time limit | 60s total; 4000 tokens per request |
| D5 | Store CV after response? | No (stateless) |
| D6 | Default LLM | Gemini; switchable via env |
| D7 | API framework | FastAPI (already in place) |
| D8 | Bullet restructuring? | No; bullet count preserved |
