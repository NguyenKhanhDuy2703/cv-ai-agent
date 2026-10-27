# CV AI Agent

Independent, stateful service that generates canonical CVs from a JD and Candidate Profile.
The AI service owns durable generation jobs, immutable input snapshots, attempts,
leases, persisted SSE events and results in its own PostgreSQL database.

## Architecture

```text
AI API -> PostgreSQL <- Independent worker -> Generation pipeline
             |                                  |
             +<------ events and result --------+
             |
        Status / SSE / Result APIs
```

The pipeline remains one-shot: normalize -> gaps -> evidence -> JD analysis ->
static RAG -> typed writers -> deterministic guard -> canonical validation/YAML.
Candidate Profile is the only source of personal facts. JD and RAG guide wording.
Template design, locale and settings are request inputs; no Render checkout,
shared TypeScript package or Render database is required.

## API

All generation routes use the existing `Authorization: Bearer <AI_SECRET_KEY>`
service authentication. An empty key keeps the existing local-development behavior.

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/v1/ai/generations` | Persist a job and return 202 with jobId and tracking URLs |
| GET | `/v1/ai/generations/{id}` | Status, attempt, timestamps, error and terminal gaps |
| GET | `/v1/ai/generations/{id}/events` | Follow or replay persisted SSE events |
| GET | `/v1/ai/generations/{id}/result` | Terminal GenerateCvResult; 409 while pending |
| POST | `/v1/ai/generate/stream` | Existing request/envelope, backed by the same job store |

New POST input: `requestId`, `jobDescription`, `profile`, `options`, `renderDefaults`.
It does not accept `generationId`; the service assigns it. The legacy POST retains
its required caller-supplied `generationId`, mapped to a separate internal jobId.
Swagger/OpenAPI at `/docs` describes the Python contracts.

Input strings are boundary-trimmed, object keys are canonicalized for hashing,
and list order is preserved. Reusing requestId with identical normalized input
returns the existing job; different input or a changed legacy generationId returns
409. Structural errors return 422 before persistence. Retry a terminal outcome by
submitting corrected/the same input under a new requestId and, for legacy calls,
a new generationId.

States: `QUEUED -> RUNNING -> NEEDS_INPUT | COMPLETED | FAILED`.
Required business gaps produce needs_input before writers run. Writers/RAG retain
existing truthful partial fallbacks. Only validated CVs produce COMPLETED.

SSE events: progress (English), gap_report (vi/en), partial_update and one persisted
terminal event: needs_input, done or error. New SSE adds `id`, jobId and attempt;
reconnect using `Last-Event-ID`. Attempts share one increasing sequence. Drafts
from an earlier attempt are provisional; the final document is authoritative.
An expired cursor/job returns 404; a cursor ahead of the event log returns 409.
The legacy stream keeps its original event types/envelope/sequence and replays
from the beginning when the same request is posted again. Heartbeats are comments.

**AI done means generated, validated and durably saved in AI storage.** It has no
cvId and does not mean a consuming application's database has saved the CV.
A backend can fetch a completed result repeatedly without calling the model again.
Disconnecting any subscriber never cancels the job.

## Run locally

```bash
uv sync --locked --extra dev
```

Copy `.env.example` to `.env` if needed; preserve existing provider/model/key settings.
Set AI_DATABASE_URL to the AI-owned PostgreSQL database. The CLI and pure pipeline
can run without this variable. API and worker startup require an up-to-date schema.

Using Docker (local database port 55432):

```bash
docker compose up -d postgres
docker compose run --rm migrate
docker compose up -d api worker
```

The explicit migration command is required; API startup never creates tables or
runs migrations. Compose reads provider/model/key values from the environment or
.env. It does not mount the host .env into the image.

Alternatively, start only postgres, activate the virtual environment and run:

```bash
alembic upgrade head
python -m src.main
# A separate terminal/process:
python -m src.worker
```

`/health/live` checks the API process. `/health/ready` checks database connectivity
and the Alembic schema revision, returning 503 when unavailable. `/health` retains
its existing response. Readiness does not certify worker availability.

Defaults: 1-second worker polling, 2 concurrent jobs per worker, 120-second total
deadline (queue included), 30-second lease, 5-second heartbeat, 2 attempts, 24-hour
retention after terminal completion. All are configurable in `.env.example`.
Worker claims use short SKIP LOCKED transactions, and every event/result write is
fenced by a current, unexpired lease. Database time governs ownership/deadlines.
A lost worker lease reruns the full pipeline on the same snapshot and canonical
IDs; model calls/output text may repeat or vary. Graceful shutdown relinquishes
work through the same recovery path. No model-level exactly-once guarantee exists.

Terminal state/result/event commit atomically. PostgreSQL enforces unique request
IDs, event sequences and one terminal event per job. Retention deletes snapshots,
events and results together. A worker must be running for recovery and physical
cleanup. Status/SSE/result reads settle overdue jobs even with workers offline;
expired results are hidden by the API even before cleanup. Idempotency
ends when retention expires. API logs omit request bodies and credentials.

## Test and CLI

```bash
python -m pytest -q
python -m src.cli parse -i cv.md -o cv.yaml
python -m src.cli validate -i cv.yaml
```

The default suite keeps pure pipeline, evidence, guards, RAG, provider, config,
auth, canonical and CLI regressions independent of PostgreSQL and a live LLM.
PostgreSQL tests are explicitly skipped without AI_TEST_DATABASE_URL.

Run real database integration tests in the disposable local database:

```bash
docker compose --profile test up -d postgres-test
# Set both variables in your shell (PowerShell: $env:NAME = "value"):
# AI_TEST_DATABASE_URL=postgresql+psycopg://cv_ai_test:cv_ai_test@localhost:55433/cv_ai_test
# AI_DATABASE_URL=<same test URL, for this migration command only>
alembic upgrade head
python -m pytest -q
```

Tests reject non-local hosts and database names without the `_test` suffix. They
truncate only AI tables; never point these variables at the Render database.
All fixtures are local synthetic data; no FE, BE or Render checkout is needed.

- `src/jobs/`: contracts, persistence, leases, retention and subscriptions.
- `src/worker.py`: independent worker entrypoint.
- `src/api/`: job routes, compatibility adapter and health.
- `src/pipeline/generation/`: generation logic, independent of persistence/HTTP.
- [Learning guide](docs/learning/README.md)
- [Fixture provenance](tests/fixtures/README.md)
- [Architecture snapshots](archify-architecture/README.md) (existing published diagrams;
  the service ownership changes in this README are authoritative).
