# Test fixtures

`canonical/en.v1.json` and `canonical/vi.v1.json` are byte-for-byte snapshots of
`packages/cv-contracts/fixtures/{en,vi}.v1.json` from the Render project, using
canonical schema version 1. They include all nine entry types and complete Render
defaults. These are synthetic contract samples, not user CVs.

Tests load these local snapshots through `tests/helpers.py`; they do not require
a Render checkout. When the canonical contract changes, update the JSON schema
and both snapshots together, verify provenance against the contract fixtures,
and run the canonical validation and generation suites.

CLI YAML/Markdown source samples remain in `tests/golden/`.
