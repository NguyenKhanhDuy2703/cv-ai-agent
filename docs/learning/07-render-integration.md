# 07 — Consumer integration

This repository exposes a standalone API, without importing Render code or reading
its database. The new interface is POST /v1/ai/generations (202), followed by GET
/v1/ai/generations/{id}, /events and /result. Authentication uses AI_SECRET_KEY.
Consumers use requestId for idempotency and Last-Event-ID for SSE replay. Event
sequence continues across attempts; attempt identifies restarted drafts.

POST /v1/ai/generate/stream remains compatible with the existing backend payload
and envelope. The AI adapter persists a job and subscribes to it. Closing that
stream does not cancel the job; reposting the same request replays stored events.
No FE/BE changes or Render migrations are part of this implementation. Existing
backend timeouts/locks remain consumer behavior until a later integration update.

AI COMPLETED/done means its validated result is durably available for 24 hours,
not that a consumer saved a CV. Consumers should persist a result idempotently by
AI job ID, and expose their own saved cvId only after that transaction succeeds.
A failed consumer save should fetch the result again instead of regenerating.
