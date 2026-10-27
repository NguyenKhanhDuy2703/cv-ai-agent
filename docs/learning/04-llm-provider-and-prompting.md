# 04 — LLM provider and typed writers

Production inference uses Gemini exclusively. AI_PROVIDER accepts only gemini;
AI_API_KEY and an explicit AI_MODEL are required when starting a worker. API/CLI
remain usable without model credentials. There is no offline provider or fallback
model name. Test providers live under tests/ and are injected explicitly.

All model calls use LLMProvider.generate_structured(schema, messages). Gemini
classifies HTTP status/network errors and retries only transient failures with a
bounded budget. JD, Summary, Experience and Projects wrap failed calls with stage,
schema and optional source item IDs. A provider error terminates the job instead
of silently generating heuristic content. Evidence guard rejection can still keep
original candidate facts and yield partial, as can unavailable optional RAG.

Read job.error and correlate worker logs using jobId/requestId/attempt. Diagnostics
include a safe code, stage, errorType, schema and source location; raw provider
messages, prompts, response text and credentials are not logged. Automatic tests
cover provider error classification, key redaction, retry correlation and the
absence of runtime fake-provider selection.
