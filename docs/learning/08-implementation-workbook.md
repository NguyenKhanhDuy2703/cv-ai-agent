# 08 — Verification workbook

Verify that contracts reject conversation fields and support three terminal events. Cover required and recommended gaps, student evidence, writer/RAG fallback and deterministic canonical IDs.

Backend tests cover ownership, requestId deduplication, one active job per owner, worker claims, atomic save/event commit, timeout fencing, restart recovery, snapshot retry and event replay after disconnect.

Frontend tests cover backend-controlled disabling of Generate, form correction after needs_input, new requestId submission, GET reconnect, page reload and opening the saved CV by cvId.

Run the Python and Render workspace suites. Test the additive SQL migration on isolated PostgreSQL; historical session data must remain unchanged.

For this Python repository, `python -m pytest -q` runs API, auth, configuration,
generation, candidate evidence, JD analysis, guards, static retrieval, provider,
canonical validation and CLI/YAML/Markdown regressions. Local fixtures and mock
providers allow the suite to run independently of a Render checkout. Render
workspace suites and database migrations are separate integration checks.
