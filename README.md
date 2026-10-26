# CV AI Agent

Stateless service that generates a new canonical RenderCV document from a job description and a candidate profile.

## One-shot flow

```text
POST /v1/cv-generations -> QUEUED -> RUNNING
  JD + Candidate Profile -> Gaps -> Evidence -> JD Analysis -> RAG
  -> Typed Section Writers -> Guard -> Canonical document
  -> Backend validates and saves Cv -> COMPLETED
```

Render Backend owns the job, immutable input snapshot, timeout and persisted event log. The AI service processes one snapshot and stores no user state. There is no conversational turn endpoint.

## API and events

Frontend creates a job using `POST /v1/cv-generations` with a stable client-generated `requestId`. Repeating the same request ID and input returns the same job; different input with that ID returns 409. Only one QUEUED/RUNNING job per owner is allowed by a database index.

- `GET /v1/cv-generations/active`: current active job.
- `GET /v1/cv-generations/:id`: authoritative status, input snapshot and result.
- `GET /v1/cv-generations/:id/events`: follow/replay events with `Last-Event-ID`.
- Backend calls `POST /v1/ai/generate/stream` using a service Bearer token.
- AI health routes remain `/health`, `/health/live`, and `/health/ready`.

Progress is always English. Gap messages follow `vi` or `en`. Events include `progress`, `gap_report`, `partial_update` and backend `status`. Exactly one terminal outcome is persisted:

| Event | Backend status | Meaning |
| --- | --- | --- |
| `needs_input` | `NEEDS_INPUT` | Missing required data. Edit the form and create a new generation. |
| `done` | `COMPLETED` | Canonical CV validated and saved; includes `cvId`. |
| `error` | `FAILED` | Generation failed or exceeded its deadline. |

Disconnecting the browser SSE subscription does not cancel the worker or the Backend→AI connection. Reconnect reads stored events without rerunning AI. A failed job can be retried with a new `requestId` and `retryOfId`, using its saved input snapshot.

## Evidence and validation

Required input: JD, name, email, target position and at least one concrete experience/project fact or complete education. Phone, location, dates and metrics are recommended.

Candidate Profile is the source of personal facts. JD/RAG guide relevance and wording. Unsupported generated claims fall back to source facts, producing a valid `partial` result where appropriate. Canonical IDs are derived from generation and source item IDs. Backend supplies template style settings and saves the validated document in the same transaction as the final job status/event.

## Development

Project layout:

- `src/api/` exposes the backend-only AI stream and health endpoints.
- `src/pipeline/generation/` owns generation, gaps, profile evidence, writers and canonical building.
- `src/core/`, `src/guard/`, `src/knowledge/`, and `src/llm/` contain shared production components.
- `tests/` contains regression tests, shared input factories and local canonical fixtures.
- [Learning guide](docs/learning/README.md) explains the implementation.
- [Architecture snapshots](archify-architecture/README.md) indexes the published diagrams and their source specifications.

```bash
pip install -e .[dev]
python -m pytest -q
python -m src.main
python -m src.cli parse -i cv.md -o cv.yaml
python -m src.cli validate -i cv.yaml
```

The Python suite uses local synthetic fixtures and mock providers. A separate
Render checkout, running backend, network connection or live LLM key is not
required. Canonical fixture provenance is documented in
[tests/fixtures/README.md](tests/fixtures/README.md).

`pyproject.toml` defines package dependencies and the optional `dev` test tools;
`uv.lock` pins them. Check the lock without installing packages using
`uv lock --check --offline`. `requirements.txt` remains available for pip-based
development setups.

Configure `AI_SECRET_KEY` on both services. `AI_MAX_BODY_SIZE` defaults to 10 MiB. Render Backend `CV_GENERATION_TIMEOUT_MS` defaults to 120000 (queue plus execution). Its database-polling worker starts with the API and recovers overdue jobs after a restart. Deploy the additive Prisma job/event migration before starting the updated backend; existing session data is retained.
