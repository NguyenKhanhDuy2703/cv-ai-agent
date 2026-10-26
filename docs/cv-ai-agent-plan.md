# Plan: Triển khai CV AI Agent (Agent Core trước, RAG sau)

## Architecture Overview & Decisions
- **Render canonical document** as primary source of truth contract (`packages/cv-contracts`).
- **MVP focus**: Experience bullets for IT software industry (`it_software`), bilingual (vi & en).
- **Proposals & Review**: Agent generates structured semantic patches; user reviews diff before applying.
- **Render Backend Integration**: Render Backend calls AI Agent via service-to-service Bearer authentication. Browser does not call agent directly.
- **Agent Core Independence**: Works fully with RAG disabled or empty retrieval (`NullKnowledgeRetriever`).
- **Provider Strategy**: Gemini for live production (`google-genai`), MockProvider for deterministic tests.
- **Patch Purity**: LLM outputs typed proposals only. Python compiles and validates semantic patches.

---

### Task 0: Repository Stabilization
- [x] Subtask 0.1: Add generated YAML files to `.gitignore` and ensure no secrets committed.
  - File: `d:/Projects/cv-ai-agent/.gitignore`
  - Verify: `git status` in `cv-ai-agent`
- [x] Subtask 0.2: Sync dependencies with `google-genai`, `jsonschema`.
  - File: `d:/Projects/cv-ai-agent/requirements.txt`, `d:/Projects/cv-ai-agent/pyproject.toml`
  - Verify: `pip check`
- [x] Subtask 0.3: Harmonize configuration and environment settings: `AI_API_KEY`, provider enum to `["mock", "gemini"]`, default `mock`, drop `openai` for now.
  - File: `d:/Projects/cv-ai-agent/src/config.py`, `d:/Projects/cv-ai-agent/.env.example`
  - Verify: `python -m pytest tests/test_config.py`
- [x] Subtask 0.4: Update API health routes to include `/health/live` and `/health/ready`, plus test suite speedup / reliability.
  - File: `d:/Projects/cv-ai-agent/src/api/server.py`, `d:/Projects/cv-ai-agent/tests/test_api_and_schemas.py`
  - Verify: `python -m pytest -q` passes without delay

---

### Task 1: Render Contract & Semantic Patch Engine
- [x] Subtask 1.1: Export and version Render Canonical JSON Schema from `@rendercv/cv-contracts` to Python agent schemas.
  - File: `d:/Projects/cv-ai-agent/src/schemas/render_cv_schema.json`, `d:/Projects/Render/packages/cv-contracts/scripts/export-schemas.mjs`
  - Verify: `node d:/Projects/Render/packages/cv-contracts/scripts/export-schemas.mjs`
- [x] Subtask 1.2: Implement Python schema validator using `jsonschema` for Render canonical documents.
  - File: `d:/Projects/cv-ai-agent/src/schemas/canonical_validator.py`
  - Verify: `python -m pytest tests/test_canonical_validator.py` on vi.v1.json & en.v1.json fixtures
- [x] Subtask 1.3: Define request & semantic patch MVP DTOs (`TailorRequest`, `SemanticPatch`, `PatchReport`).
  - File: `d:/Projects/cv-ai-agent/src/schemas/canonical_dto.py`
  - Verify: Type check and unit tests
- [x] Subtask 1.4: Implement semantic patch applier with stable ID lookup, beforeHash verification, locked path protection, and document re-validation.
  - File: `d:/Projects/cv-ai-agent/src/schemas/patch_applier.py`
  - Verify: `python -m pytest tests/test_patch_applier.py` (verify non-destructive roundtrip on Render fixtures)

---

### Task 2: Candidate Evidence Extraction & JD Analyzer
- [x] Subtask 2.1: Implement Candidate Evidence Extractor extracting company, position, dates, technologies, metrics, and highlights with stable deterministic IDs and JSON paths.
  - File: `d:/Projects/cv-ai-agent/src/core/evidence_extractor.py`
  - Verify: `python -m pytest tests/test_evidence_extractor.py`
- [x] Subtask 2.2: Implement structured JD Analyzer (role family, seniority, required/preferred skills, responsibilities, keywords, excerpts).
  - File: `d:/Projects/cv-ai-agent/src/core/jd_analyzer.py`
  - Verify: `python -m pytest tests/test_jd_analyzer.py`

---

### Task 3: Experience Bullet Writer & Deterministic Guards
- [x] Subtask 3.1: Implement Experience Bullet Writer optimizing 1 Experience entry at a time with typed bullet proposals requiring evidence IDs.
  - File: `d:/Projects/cv-ai-agent/src/core/experience_writer.py`
  - Verify: `python -m pytest tests/test_experience_writer.py`
- [x] Subtask 3.2: Implement comprehensive deterministic guards (numeric/metric fabrication, company/title/dates, skills evidence, ban terms, bullet count/length).
  - File: `d:/Projects/cv-ai-agent/src/guard/deterministic_guard.py`
  - Verify: `python -m pytest tests/test_deterministic_guard.py`

---

### Task 4: Agent Core Pipeline with Retrieval Interface
- [x] Subtask 4.1: Define `KnowledgeRetriever` protocol and `NullKnowledgeRetriever`.
  - File: `d:/Projects/cv-ai-agent/src/knowledge/retriever_protocol.py`, `d:/Projects/cv-ai-agent/src/knowledge/null_retriever.py`
  - Verify: `python -m pytest tests/test_null_retriever.py`
- [x] Subtask 4.2: Build end-to-end Agent Core orchestrator (`TailorPipeline`) connecting validator -> evidence -> JD -> retriever -> writer -> guard -> semantic patch builder -> diff report.
  - File: `d:/Projects/cv-ai-agent/src/pipeline/agent_orchestrator.py`
  - Verify: `python -m pytest tests/test_agent_orchestrator.py`

---

### Task 5: AI API Hardening & SSE Streaming
- [x] Subtask 5.1: Create shared application service powering both sync (`POST /v1/ai/tailor`) and streaming (`POST /v1/ai/tailor/stream`).
  - File: `d:/Projects/cv-ai-agent/src/api/service.py`
  - Verify: Unit test service directly
- [x] Subtask 5.2: Implement standardized SSE envelope (`type`, `runId`, `sequence`, `data`), single terminal event (`completed` or `failed`), client disconnect cancellation, body size limit, and Bearer auth.
  - File: `d:/Projects/cv-ai-agent/src/api/routes.py`, `d:/Projects/cv-ai-agent/src/api/server.py`
  - Verify: `python -m pytest tests/test_api_v1.py`

---

### Task 6: Knowledge Corpus & Lexical Retrieval
- [x] Subtask 6.1: Clean IT knowledge pack with version, language (vi/en), source, licensing, marking examples clearly.
  - File: `d:/Projects/cv-ai-agent/src/knowledge/corpus/it_software.yaml`
  - Verify: Inspection & validation
- [x] Subtask 6.2: Implement `StaticKnowledgeRetriever` and lexical matching with Top-K and threshold filtering, plus 20 evaluation test cases.
  - File: `d:/Projects/cv-ai-agent/src/knowledge/static_retriever.py`, `d:/Projects/cv-ai-agent/tests/test_knowledge_eval.py`
  - Verify: `python -m pytest tests/test_knowledge_eval.py` (Recall@5 >= 85%)

---

### Task 7: Render Backend Review-and-Apply Integration & OCC
- [x] Subtask 7.1: Implement Render Backend endpoints `POST /v1/cvs/:id/tailor` and `POST /v1/cvs/:id/tailor/apply` with OCC conflict handling (409 on `baseVersion` / `beforeHash` mismatch) and document schema validation before commit.
  - File: `d:/Projects/Render/MODULE_BE/src/cv/cv.controller.ts`, `d:/Projects/Render/MODULE_BE/src/cv/cv.service.ts`
  - Verify: `npm --prefix d:/Projects/Render/MODULE_BE run test` or controller/service unit tests
