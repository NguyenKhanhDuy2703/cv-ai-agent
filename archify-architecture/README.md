# Architecture Snapshots

Open [index.html](index.html) to browse the interactive **Archify Portal Dashboard** for all 5 diagrams.
Each HTML file is self-contained with zero CDN dependencies; the index loads diagrams using relative paths.

| Published Diagram | Type | Preserved Source Specification | Description |
| --- | --- | --- | --- |
| [System Architecture](cv-system.html) | Architecture | [cv-system.json](specs/cv-system.json) | Dual-process system architecture: FastAPI Gateway, PostgreSQL Job Store, Independent Generation Worker (`SKIP LOCKED`), Generation Pipeline, Deterministic Guards, Static RAG, and Live Gemini LLM Provider (`operations.py`). |
| [Generation Pipeline](cv-pipeline.html) | Workflow | [cv-pipeline.json](specs/cv-pipeline.json) | 6-phase generation workflow: Intake & Snapshot, Gap Detection & Evidence Store, Strategic Planning & Section Writers (`generate_at_stage`), 0% Fact Guard, Canonical Validator, and Atomic Result Persistence. |
| [Durable SSE Sequence](cv-sequence.html) | Sequence | [cv-sequence.json](specs/cv-sequence.json) | End-to-end durable generation lifecycle: POST 202 Accepted, DB snapshot, Worker claim (`SKIP LOCKED`) & lease, `JOB_CONTEXT` tracking, replayable SSE stream with `Last-Event-ID`, and safe diagnostic failure persistence. |
| [API Subsystem Flow](cv-api.html) | Architecture | [cv-api.json](specs/cv-api.json) | FastAPI Gateway with asyncpg connection pooling, health readiness probes, durable job endpoints (`POST /v1/ai/generations`, `GET /events`, `GET /result`), and `JobRepository`. |
| [Codebase Hierarchy](cv-modules.html) | Tree | [cv-modules.json](specs/cv-modules.json) | Codebase hierarchy decomposition covering all 10 modules in `src/` (including `llm/operations.py`, `jobs`, `worker.py`, `api`, `guard`, `llm`, `pipeline`, `schemas`), alembic migrations, and operational entrypoints. |

The five specifications are pinned to Git commit [`feabee2dc795dd2dd0dd678b5d5707408c9efac5`](https://github.com/khanhduy1407/cv-ai-agent/commit/feabee2dc795dd2dd0dd678b5d5707408c9efac5) and verified against repository evidence. Intermediate renders, receipts, and browser logs are disposable.

See the [project README](../README.md) and [learning guide](../docs/learning/README.md) for the one-shot generation contract and test execution.
