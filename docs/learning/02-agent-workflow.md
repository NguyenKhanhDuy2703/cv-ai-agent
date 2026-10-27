# 02 — One-shot workflow

The API validates structure, normalizes input, deduplicates requestId and persists
an immutable snapshot before accepting a job. A separate worker claims it.

The pipeline detects gaps, builds candidate evidence, analyzes the JD, retrieves
guidance, plans sections, runs typed writers, guards claims and builds/validates
the canonical document. Missing required business data returns needs_input before
writers run; corrected input starts a new job. There are no conversational turns.

A valid success/partial result, terminal status and done event commit together in
AI storage. needs_input and error are the other terminal events. AI done contains
no cvId: the consuming backend must save the CV in its own application afterward.
Model failure can produce the existing truthful partial fallback; an unhandled
pipeline error fails the job without persisting raw exception text.

SSE only reads persisted events. Worker loss triggers a bounded full-pipeline
retry with the same snapshot/IDs; it does not resume individual section checkpoints.
