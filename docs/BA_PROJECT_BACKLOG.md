# CV AI Agent — BA Project Plan & Delivery Backlog

**Version:** 1.0  
**Date:** 2026-10-22  
**Owner:** Solo developer  
**Delivery approach:** Vertical slices, contract-first, evidence-grounded AI  

## 1. Product goal

Build an AI service that receives a canonical Render CV and a target Job Description, retrieves relevant CV-writing knowledge, proposes evidence-grounded improvements, validates every change, and integrates with the Render API to create or update a renderable CV safely.

The service must never invent candidate facts. Knowledge retrieved from RAG may guide wording and structure, but only candidate evidence may support claims about the candidate.

## 2. MVP outcome

At the end of MVP, a signed-in Render user can:

1. Select an existing CV.
2. Paste a Job Description.
3. Request optimization of one Experience section.
4. Watch progress through SSE.
5. Review before/after changes with evidence references.
6. Approve or reject proposed patches.
7. Save the approved version without overwriting a newer edit.
8. Render/download the result through the existing Render application.

Full autonomous CV creation, document upload, multi-provider routing, and advanced reranking are post-MVP unless explicitly promoted.

## 3. Product principles

- **Render owns user data and authorization.** The agent does not accept browser session cookies or decide CV ownership.
- **Agent is stateless for MVP.** It processes a request and returns patches/report; Render persists the CV.
- **Contract-first.** Render's canonical document schema is the source of truth.
- **Patch, do not regenerate blindly.** The LLM returns typed content; application code builds controlled patches.
- **Evidence before prose.** Every candidate claim must link to candidate evidence.
- **Human approval by default.** `autoApply` remains disabled during MVP.
- **RAG provides writing knowledge, not candidate achievements.**
- **Deterministic validation surrounds probabilistic generation.**

## 4. Actors

| Actor | Need |
|---|---|
| Candidate | Tailor a truthful CV to a JD and understand every change |
| Render frontend | Stream progress, show gaps/diffs, submit approvals |
| Render backend | Enforce ownership, validate contracts, persist revisions and render artifacts |
| CV AI Agent | Analyze, retrieve, propose and validate content changes |
| Administrator | Control models, quotas, knowledge versions and operational health |

## 5. Scope

### MVP in scope

- Canonical Render document input.
- Text JD input.
- JD structured analysis.
- Experience bullet tailoring.
- Industry/role knowledge retrieval.
- Evidence-grounded output.
- Semantic patch response.
- SSE progress.
- Render backend integration.
- Manual approval.
- Schema, factuality and concurrency validation.
- Mock-provider integration tests and a small evaluation set.

### MVP out of scope

- Scraping jobs from arbitrary URLs.
- Parsing PDF/DOCX CVs or JDs.
- Autonomous submission to job portals.
- Training or fine-tuning a model.
- Using other candidates' CVs as knowledge.
- Automatic publication without review.
- Full ATS vendor emulation or a promise of an exact ATS score.
- DOCX export.

## 6. Target workflow

```text
User selects CV + enters JD
        ↓
Render verifies user and loads canonical document/baseVersion
        ↓
Render calls cv-ai-agent using service authentication
        ↓
Agent validates request and extracts candidate evidence
        ↓
Agent analyzes JD and retrieves relevant knowledge chunks
        ↓
Agent proposes typed bullet rewrites
        ↓
Guards validate facts, entities, skills, dates and output schema
        ↓
Agent returns semantic patches + report + evidence/citation IDs
        ↓
Render displays diff for approval
        ↓
Render validates and applies against the same baseVersion
        ↓
Render persists a revision and renders/exports the CV
```

## 7. Definition of Done

A task is Done only when:

- Acceptance criteria are demonstrably satisfied.
- Unit tests cover success and failure paths.
- No real paid LLM call is required in the default test suite.
- Public contracts and environment variables are documented.
- Errors do not expose CV content, secrets, stack traces or provider payloads.
- New behavior has structured logs using request/run IDs.
- Existing tests remain green.
- The relevant README/API documentation is updated in the same task.

## 8. Delivery roadmap

| Milestone | Goal | Estimated solo effort | Exit gate |
|---|---|---:|---|
| M0 | Stabilize repository and current service | 2–3 days | Reproducible install; tests terminate and pass |
| M1 | Align contracts with Render | 4–6 days | Render fixture can round-trip through agent unchanged |
| M2 | Deliver one evidence-grounded tailoring slice | 5–7 days | One Experience entry produces safe reviewable patches |
| M3 | Build real RAG MVP | 5–7 days | Relevant chunks retrieved with citations and measured quality |
| M4 | Integrate Render and approval workflow | 5–8 days | User can request, review and apply tailoring end to end |
| M5 | Harden and evaluate | 4–6 days | Security, failure, regression and operational gates pass |

Expected MVP duration for one developer: approximately 5–7 focused weeks, excluding product feedback and deployment approvals.

---

## 9. Prioritized backlog

## Epic E0 — Repository stabilization

### AGENT-001 — Checkpoint the current Python migration

**Priority:** P0  
**Estimate:** 0.5 day  
**Dependencies:** None

**User value:** Development can proceed without losing or mixing the large TypeScript-to-Python migration currently present in the working tree.

**Acceptance criteria:**

- Current intended Python files and intended TypeScript deletions are reviewed.
- Generated outputs such as `my_tailored_cv.yaml` and `my_report.yaml` are either classified as fixtures or ignored.
- The current state is committed on a named feature branch or saved as an explicit checkpoint.
- No secrets or local `.env` file are committed.

### AGENT-002 — Make installation and configuration consistent

**Priority:** P0  
**Estimate:** 1 day  
**Dependencies:** AGENT-001

**Acceptance criteria:**

- `.env.example`, README and `Settings` use the same variable names.
- Gemini configuration has one documented key variable.
- `google-genai` is present in project dependencies when Gemini is supported.
- Unsupported providers are rejected at startup or fully implemented.
- Development default uses an explicitly named mock provider, not a misleading production provider.
- Startup validation reports missing variable names without printing their values.

### AGENT-003 — Fix the automated test runner and hanging API tests

**Priority:** P0  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-002

**Acceptance criteria:**

- `python -m pytest -q` terminates without hanging.
- Health and root redirect tests complete on Windows.
- All 55 currently collected tests either pass or failed tests have approved issue IDs.
- CI command is documented and does not depend on a globally broken `pytest.exe` launcher.
- A test timeout prevents indefinite hangs.

### AGENT-004 — Remove API/documentation drift

**Priority:** P0  
**Estimate:** 0.5 day  
**Dependencies:** AGENT-002

**Acceptance criteria:**

- README documents only endpoints that exist.
- One canonical route name is selected for synchronous tailoring and one for streaming.
- OpenAPI examples match the actual Pydantic request models.
- Health response distinguishes liveness from provider readiness.

---

## Epic E1 — Canonical Render contract

### AGENT-101 — Export and version the Render document JSON Schema

**Priority:** P0  
**Estimate:** 1 day  
**Dependencies:** AGENT-003

**Acceptance criteria:**

- The schema is generated from `@rendercv/cv-contracts`, not manually copied.
- The agent stores a versioned schema such as `contracts/rendercv-document.v1.schema.json`.
- Schema version is included in requests and responses.
- At least the Render Vietnamese and English fixtures validate in Python.
- A schema update procedure is documented.

### AGENT-102 — Define the integration request and response contracts

**Priority:** P0  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-101

**Request must include:**

- `requestId`
- `cvId`
- `baseVersion`
- `schemaVersion`
- canonical `document`
- `jobDescription`
- `instruction`
- `language`
- `industry`
- `lockedPaths`

**Response must include:**

- `runId`
- `baseVersion`
- proposed patches
- change report
- validation result
- evidence IDs
- RAG knowledge chunk IDs
- warnings/partial failures

**Acceptance criteria:**

- Pydantic models exist for the versioned contract.
- Unknown contract versions return a stable 422 error.
- The contract does not require user cookies or provider credentials.
- Examples validate against OpenAPI.

### AGENT-103 — Implement Render document adapter

**Priority:** P0  
**Estimate:** 2 days  
**Dependencies:** AGENT-102

**Acceptance criteria:**

- Adapter reads canonical `cv.sections` and all supported entry types.
- Stable section and entry IDs are preserved.
- Existing Render document can be converted to internal evidence and back without content loss.
- Design, locale and settings remain unchanged during content tailoring.
- Unsupported entry types are preserved and reported rather than deleted.
- Round-trip tests use real Render fixtures.

### AGENT-104 — Define semantic patch format and patch applier

**Priority:** P0  
**Estimate:** 2 days  
**Dependencies:** AGENT-103

**Acceptance criteria:**

- Patch targets stable `sectionId` and `entryId`, not only array indexes.
- Patch contains `beforeHash` and fails if the target changed.
- Locked paths cannot be patched.
- Patch applier changes only the declared field.
- Application produces a machine-readable before/after diff.
- Result is revalidated using the canonical Render schema.

---

## Epic E2 — Evidence-grounded AI vertical slice

### AGENT-201 — Extract candidate evidence from one Experience entry

**Priority:** P0  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-103

**Acceptance criteria:**

- Company, position, dates, location, summary and every highlight receive stable evidence IDs.
- Evidence records retain their source paths.
- Original text is never sent to logs.
- Empty or insufficient entries return a gap report rather than fabricated content.

### AGENT-202 — Strengthen JD analysis

**Priority:** P0  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-102

**Acceptance criteria:**

- Structured output distinguishes required skills, preferred skills, responsibilities, seniority and role family.
- Each extracted item contains the supporting JD excerpt or location.
- Prompt instructions inside the JD are treated as untrusted content.
- Oversized JD input is rejected with a stable error.
- Mock-provider tests cover Vietnamese and English JDs.

### AGENT-203 — Generate Experience rewrite proposals with provenance

**Priority:** P0  
**Estimate:** 2 days  
**Dependencies:** AGENT-201, AGENT-202

**Acceptance criteria:**

- The model returns typed bullet proposals, not YAML.
- Every proposal declares `evidenceIds`.
- Bullet count is preserved for MVP.
- Company, title and dates cannot be modified by this operation.
- JD keywords are used only when supported by evidence.
- Provider failure returns a partial-failure report and preserves original text.

### AGENT-204 — Expand deterministic guards

**Priority:** P0  
**Estimate:** 2 days  
**Dependencies:** AGENT-203

**Rules:** Metric, named entity, skill evidence, date consistency, banned term, evidence ID, length and output schema.

**Acceptance criteria:**

- Fabricated numbers are rejected.
- Fabricated tools, certifications, company names and job titles are rejected.
- Unknown evidence IDs are rejected.
- Rejected proposals retain the original bullet and appear in the report.
- A mutation test rejects at least 95% of the agreed fabricated-claim fixture set.

### AGENT-205 — Produce semantic patches and change report

**Priority:** P0  
**Estimate:** 1 day  
**Dependencies:** AGENT-104, AGENT-204

**Acceptance criteria:**

- Only guard-approved proposals become patches.
- Report explains accepted, rejected and unchanged bullets.
- Each accepted change includes evidence and knowledge references.
- Applying all patches yields a valid Render document.
- Re-running with the same mock input is deterministic.

---

## Epic E3 — Real RAG MVP

Detailed architecture, corpus governance, retrieval design and the `RAG-001` through `RAG-015` execution backlog are defined in `docs/RAG_DESIGN_PLAN.md`.

### AGENT-301 — Define the curated knowledge corpus and governance

**Priority:** P1  
**Estimate:** 1 day  
**Dependencies:** AGENT-202

**Acceptance criteria:**

- `knowledge/manifest.yaml` records ID, title, source, license, language, industry, role family and version.
- Content without an approved source/license is excluded.
- Candidate CVs are explicitly prohibited from the shared knowledge corpus.
- Initial corpus covers Experience writing for IT/software in Vietnamese and English.

### AGENT-302 — Build Markdown-aware ingestion and chunking

**Priority:** P1  
**Estimate:** 1.5–2 days  
**Dependencies:** AGENT-301

**Acceptance criteria:**

- Documents are split by headings and semantic list/table boundaries.
- Chunk size and overlap are configurable.
- Every chunk retains document and section metadata.
- Ingestion is idempotent by content hash and version.
- Deleted/disabled document versions no longer appear in retrieval.

### AGENT-303 — Add embedding and vector-store abstractions

**Priority:** P1  
**Estimate:** 1.5–2 days  
**Dependencies:** AGENT-302

**Acceptance criteria:**

- Embedding provider is hidden behind an interface and mockable.
- PostgreSQL/pgvector adapter stores embedding plus metadata.
- Database schema is isolated from Render business tables.
- Batch ingestion, retry and failure reporting are supported.
- No API key or document content is written to logs.

### AGENT-304 — Implement hybrid retrieval

**Priority:** P1  
**Estimate:** 2 days  
**Dependencies:** AGENT-303

**Acceptance criteria:**

- Query combines target role, JD requirements, section type and original bullet.
- Retrieval supports language, industry, seniority and section filters.
- Vector and lexical results are merged and deduplicated.
- Top-K is configurable and defaults to a small bounded value.
- Response exposes chunk IDs and scores.

### AGENT-305 — Integrate retrieval into Experience tailoring

**Priority:** P1  
**Estimate:** 1 day  
**Dependencies:** AGENT-205, AGENT-304

**Acceptance criteria:**

- Only retrieved chunks are added to the prompt.
- RAG content is labelled as writing guidance, not candidate evidence.
- Output report records used chunk IDs.
- Disabling RAG still produces a valid evidence-grounded result.
- RAG cannot add unsupported candidate facts.

### AGENT-306 — Create retrieval evaluation set

**Priority:** P1  
**Estimate:** 1 day  
**Dependencies:** AGENT-304

**Acceptance criteria:**

- At least 20 query/expected-chunk cases exist.
- Evaluation reports Recall@K and irrelevant-result rate.
- Baseline thresholds are agreed and recorded.
- Evaluation runs without a live LLM call.

---

## Epic E4 — Production AI API

### AGENT-401 — Consolidate synchronous and streaming services

**Priority:** P1  
**Estimate:** 1.5 days  
**Dependencies:** AGENT-205

**Acceptance criteria:**

- Sync and SSE endpoints execute the same application service.
- SSE events use one versioned envelope with `runId` and monotonically increasing sequence.
- Terminal event is exactly one of `completed` or `failed`.
- Client disconnect explicitly cancels the pipeline/provider task.
- Queue size is bounded.

### AGENT-402 — Add service-to-service authentication

**Priority:** P1  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-401

**Acceptance criteria:**

- AI endpoints reject missing or invalid service credentials.
- Credentials are read only from environment/secret management.
- Authentication errors do not reveal credential details.
- `/health/live` remains available to infrastructure; readiness policy is documented.
- Key rotation supports overlap of current and next credentials.

### AGENT-403 — Add request safety controls

**Priority:** P1  
**Estimate:** 1.5 days  
**Dependencies:** AGENT-401

**Acceptance criteria:**

- Request body, JD, history and document size limits are enforced.
- Per-client rate limiting is implemented.
- Provider time and token budgets are enforced.
- Raw provider exceptions are mapped to stable safe errors.
- Logs contain IDs, duration, status and counts—not CV/JD bodies.

### AGENT-404 — Implement provider readiness and degradation reporting

**Priority:** P1  
**Estimate:** 1 day  
**Dependencies:** AGENT-002, AGENT-401

**Acceptance criteria:**

- Readiness detects invalid configuration without making an expensive generation call.
- Mock provider is marked non-production.
- If JD analysis or RAG fails, response marks the exact degraded capability.
- API cannot report an unchanged fallback as a fully successful tailored CV.

---

## Epic E5 — Render integration and automation

### AGENT-501 — Define Render-to-agent service contract

**Priority:** P1  
**Estimate:** 1 day  
**Dependencies:** AGENT-102, AGENT-402

**Acceptance criteria:**

- Render sends canonical document and base version after checking ownership.
- Agent does not receive browser cookies.
- Correlation/request IDs propagate across both services.
- Timeout, retry and error ownership are documented.

### AGENT-502 — Add Render backend tailoring endpoint

**Priority:** P1  
**Estimate:** 2 days  
**Dependencies:** AGENT-501

**Proposed route:** `POST /api/v1/cvs/:id/tailor`

**Acceptance criteria:**

- Endpoint requires authenticated CV ownership.
- Backend loads the current document and version itself.
- Request forwards only approved fields to the agent.
- Agent timeout/cancellation is handled safely.
- No CV mutation occurs during proposal generation.

### AGENT-503 — Build frontend review and approval flow

**Priority:** P1  
**Estimate:** 2–3 days  
**Dependencies:** AGENT-502

**Acceptance criteria:**

- User sees progress, gaps, before/after diff and validation warnings.
- Each proposal can be accepted or rejected.
- Evidence and knowledge-source labels are visible.
- Closing/cancelling does not apply changes.
- Accessibility and keyboard navigation are covered.

### AGENT-504 — Apply approved patches with concurrency control

**Priority:** P1  
**Estimate:** 1.5–2 days  
**Dependencies:** AGENT-104, AGENT-503

**Proposed route:** `POST /api/v1/cvs/:id/tailor/apply`

**Acceptance criteria:**

- Apply requires original `baseVersion` and patch `beforeHash` values.
- A changed document returns 409 and applies nothing.
- Render validates the final canonical document before saving.
- Approved changes are applied transactionally.
- Original CV can be recovered from revision history or an explicit duplicate.

### AGENT-505 — Add autonomous duplicate-and-tailor job

**Priority:** P2  
**Estimate:** 2–3 days  
**Dependencies:** AGENT-504, AGENT-603

**Acceptance criteria:**

- Automation creates a duplicate; it never overwrites the source CV.
- Mutation calls use an idempotency key.
- Job records source CV, target JD, model/prompt/knowledge versions and result CV.
- Failed jobs can be retried without producing duplicate CVs.
- `autoApply` requires a separate policy flag and all blocking validators to pass.

### AGENT-506 — Trigger render/export validation

**Priority:** P2  
**Estimate:** 1–2 days  
**Dependencies:** AGENT-504

**Acceptance criteria:**

- Saved tailored CV can be rendered through the Render application.
- Compile failure marks the run incomplete and preserves the previous valid revision.
- Result records page count and render diagnostics.
- User can download the same validated artifact shown in preview.

---

## Epic E6 — Quality, operations and governance

### AGENT-601 — Build the quality evaluation suite

**Priority:** P1  
**Estimate:** 2 days  
**Dependencies:** AGENT-205, AGENT-306

**Acceptance criteria:**

- At least 10 Vietnamese and 10 English CV/JD cases exist.
- Suite measures schema validity, fact preservation, fabricated claims, keyword coverage and edit acceptance suitability.
- Results are compared against a stored baseline.
- CI fails on agreed blocking regressions.

### AGENT-602 — Add observability and cost metrics

**Priority:** P1  
**Estimate:** 1–1.5 days  
**Dependencies:** AGENT-401

**Acceptance criteria:**

- Metrics include latency per stage, provider errors, retries, token usage, rejected patches and retrieval duration.
- Metrics do not contain PII.
- Logs correlate by `requestId` and `runId`.
- Alert thresholds are documented.

### AGENT-603 — Add run persistence and audit records

**Priority:** P2  
**Estimate:** 2 days  
**Dependencies:** AGENT-402, AGENT-602

**Acceptance criteria:**

- Store metadata, hashes, versions, metrics and decisions—not raw CV/JD unless explicitly approved.
- Retention duration is configurable.
- User deletion propagates to retained run data.
- Audit records distinguish user approval from automatic application.

### AGENT-604 — Security and privacy review

**Priority:** P1  
**Estimate:** 1.5–2 days  
**Dependencies:** AGENT-403, AGENT-504

**Acceptance criteria:**

- Threat model covers prompt injection, cross-tenant access, data exfiltration, oversized input and malicious YAML.
- YAML aliases/depth and unsafe types are bounded.
- Secrets and PII do not appear in logs or errors.
- Service permissions follow least privilege.
- Manual security checklist and automated negative tests pass.

---

## 10. Recommended execution order

Work in this order and do not start the next gate until the previous gate passes:

### Gate G0 — Stable baseline

1. AGENT-001
2. AGENT-002
3. AGENT-003
4. AGENT-004

### Gate G1 — Shared language with Render

5. AGENT-101
6. AGENT-102
7. AGENT-103
8. AGENT-104

### Gate G2 — One trustworthy AI outcome

9. AGENT-201
10. AGENT-202
11. AGENT-203
12. AGENT-204
13. AGENT-205

### Gate G3 — Real retrieval

14. AGENT-301
15. AGENT-302
16. AGENT-303
17. AGENT-304
18. AGENT-305
19. AGENT-306

### Gate G4 — End-to-end product flow

20. AGENT-401
21. AGENT-402
22. AGENT-403
23. AGENT-404
24. AGENT-501
25. AGENT-502
26. AGENT-503
27. AGENT-504

### Gate G5 — MVP release

28. AGENT-601
29. AGENT-602
30. AGENT-604
31. AGENT-506

### Post-MVP automation

32. AGENT-603
33. AGENT-505

## 11. First two-week sprint proposal

### Sprint goal

Establish a reliable baseline and make the agent understand the exact Render document contract.

### Sprint backlog

| Order | Task | Expected output |
|---:|---|---|
| 1 | AGENT-001 | Safe checkpoint of current migration |
| 2 | AGENT-002 | Reproducible environment/configuration |
| 3 | AGENT-003 | Non-hanging green test suite |
| 4 | AGENT-004 | Accurate README/OpenAPI routes |
| 5 | AGENT-101 | Versioned Render JSON Schema |
| 6 | AGENT-102 | Approved integration DTOs |
| 7 | AGENT-103 | Render document adapter and round-trip tests |
| 8 | AGENT-104 | Semantic patch format and safe patch applier |

### Sprint review demonstration

Given a real Render fixture, the agent API validates it, converts it to its internal representation, proposes a manually constructed test patch, applies the patch by stable IDs, validates the result, and proves that design/locale/settings and unrelated CV content remain unchanged.

## 12. BA decisions requiring confirmation before G4

These decisions do not block G0–G2 but must be settled before full integration:

1. Should applying AI changes always create a new CV revision, or create a duplicated CV by default?
2. Which service authentication method will Render and the agent use in deployment: shared API key, signed JWT or infrastructure identity?
3. What CV/JD metadata may be retained for audit, and for how long?
4. Is `autoApply` allowed for any user tier in the first release?
5. Which sources are approved for the RAG knowledge corpus?
6. What are the release thresholds for fabricated-claim rate, schema-valid output and retrieval Recall@K?

## 13. MVP success metrics

| Metric | Initial target |
|---|---:|
| Canonical schema-valid outputs | 100% |
| Fabricated numeric claims in evaluation | 0% |
| Fabricated named entities/skills in evaluation | < 2% and no blocking case |
| Patch apply conflicts handled atomically | 100% |
| Relevant knowledge in Top-5 retrieval | ≥ 85% of evaluation queries |
| Successful runs with a terminal SSE event | ≥ 99% excluding provider outages |
| P95 tailoring latency for one Experience entry | ≤ 20 seconds |
| User-visible changes carrying evidence IDs | 100% |

## 14. Main project risks

| Risk | Impact | Mitigation |
|---|---|---|
| Python schema drifts from Render TypeScript schema | Invalid or lossy CVs | Generate and version schema; contract fixtures in both repos |
| Model invents unsupported skills or achievements | Loss of trust | Evidence IDs, deterministic guards, manual approval |
| RAG examples become candidate facts | Hallucination | Separate evidence and knowledge channels in prompt and code |
| CV changes during generation | User work overwritten | `baseVersion`, `beforeHash`, atomic apply |
| Provider outage is reported as success | Silent poor output | Explicit degraded/partial status and readiness |
| SSE client disconnect leaves costly work running | Cost/resource leak | Cancellation and bounded queues |
| Knowledge sources have unclear rights | Legal/content risk | Manifest with source and license approval |
| Current uncommitted migration is lost or mixed | Delivery risk | AGENT-001 before implementation |

