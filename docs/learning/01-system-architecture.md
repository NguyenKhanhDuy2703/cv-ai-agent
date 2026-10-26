# 01 — System architecture

The browser creates a one-shot generation job on Render Backend and separately subscribes to its persisted events. Backend owns the immutable input snapshot, deadline, status and saved CV.

```text
Frontend -> POST /v1/cv-generations
Frontend -> GET /v1/cv-generations/{id}/events (replayable SSE)
Backend  -> POST /v1/ai/generate/stream (service Bearer token)
Agent    -> progress/gaps/partial/result
Backend  -> validate canonical document -> create Cv -> add cvId to done
```

Style ownership stays in Render: backend passes `design`, `locale`, and `settings` from the chosen template. The LLM never chooses presentation settings.

The database allows one QUEUED/RUNNING job per owner. requestId prevents duplicate jobs. Workers claim jobs atomically and deadlines release stuck jobs. Browser disconnect does not cancel generation; Last-Event-ID resumes observation.
