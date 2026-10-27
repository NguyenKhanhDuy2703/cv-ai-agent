# 08 — Verification workbook

Run python -m pytest -q for pure generation, evidence, JD, guard, retrieval,
provider, auth, config, canonical validator and CLI regressions. Fixtures and mock
providers require no Render checkout or live LLM key.

Enable PostgreSQL coverage with AI_TEST_DATABASE_URL pointing to the local,
disposable *_test database described in the [README](../../README.md). Apply
Alembic migrations explicitly using AI_DATABASE_URL set to that same test URL.
The database fixture truncates only AI-owned tables before each integration test.

Verify concurrent create deduplication/conflicts, SKIP LOCKED claims, lease loss,
old-worker fencing, bounded recovery, deadlines, atomic result/event commits,
retention cascade, and status/result retrieval after fresh database connections.
Cover SSE replay/heartbeats/order, terminal uniqueness, localized gaps and legacy
envelope compatibility. Disconnect must leave execution running.

Manual acceptance: run API and worker separately, create a mock job, disconnect,
restart a process and retrieve the result by job ID. A hard-killed worker can
recover after lease expiry; canonical IDs remain stable, generated wording need
not be identical. PostgreSQL readiness checks schema revision. No tests or
migrations require changing FE, BE or any Render database.
