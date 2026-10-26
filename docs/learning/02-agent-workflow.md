# 02 — One-shot workflow

The Core Agent normalizes a single request, detects gaps, builds candidate evidence, analyzes the JD, retrieves guidance, plans sections, calls typed writers, guards claims and builds/validates the canonical document.

Missing required data returns terminal `needs_input` before writers run. The frontend edits the input form and submits a separate generation. No history, draft conversation or turns are accepted.

Valid output may be `success` or `partial`. Backend validates and saves it before exposing `done`. Provider failure or deadline expiry becomes `error`.
