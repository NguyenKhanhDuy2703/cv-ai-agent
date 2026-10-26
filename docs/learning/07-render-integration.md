# 07 — Render integration

POST `/v1/cv-generations` creates a job and returns HTTP 202. GET `/v1/cv-generations/:id` reads authoritative status, input and result. GET `/v1/cv-generations/:id/events` subscribes using Last-Event-ID. GET `/v1/cv-generations/active` supplies the Generate button lock.

States: QUEUED → RUNNING → NEEDS_INPUT | COMPLETED | FAILED. The database allows one active job per owner. Repeating the same requestId and input returns the existing job; conflicts return 409.

The worker runs independently of SSE subscribers. Events are stored before sending. Browser reconnect or reload does not start another AI run. CV_GENERATION_TIMEOUT_MS defaults to 120000; overdue jobs are failed even after a worker restart.

Only a validated, transactionally saved CV produces done with cvId. needs_input returns to the form for a new generation. error permits a new job using retryOfId and a fresh requestId to reuse the saved snapshot.
