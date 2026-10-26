# 06 — Guardrails and evaluation

`DeterministicGuard` checks evidence IDs, cross-entry isolation, metrics, dates, company/title names, certifications, technologies, length, and banned phrases.

A rejected generated claim is never written into the canonical CV. The original candidate fact remains, a warning is recorded, and the result may be `partial`.

Tests should cover fabricated metrics, companies, dates, skills, and certifications; JD-only and RAG-only facts; stable IDs; writer/RAG failure; and canonical validation.
