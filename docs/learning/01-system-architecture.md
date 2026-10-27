# 01 — System architecture

The AI service owns durable generation state in a dedicated PostgreSQL database.
API and worker are separate processes; no browser/backend stream owns execution.

```text
Consumer -> POST /v1/ai/generations -> persisted QUEUED job
Worker -> claim/lease -> pipeline -> atomic result + terminal event
Consumer -> GET status / events / result
```

The existing POST /v1/ai/generate/stream is an adapter over the same store. Its
contract remains unchanged, while disconnect no longer cancels processing.
Consumer applications own their users and final CV records. They pass design,
locale and settings; the LLM never chooses style. AI neither accesses Render's
storage nor enforces a Render user's active-job lock. It deduplicates requestId
for the one authenticated consumer and bounds execution through worker concurrency.

Use API/worker migrations only against AI storage. Core generation/CLI remain
independent of PostgreSQL. See [runtime instructions](../../README.md).
