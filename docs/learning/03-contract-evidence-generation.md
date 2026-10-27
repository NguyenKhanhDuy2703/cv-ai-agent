# 03 — Contract and evidence

Python contracts live in `src/schemas/generation.py` and `src/jobs/contracts.py`, published through OpenAPI. The new job API accepts requestId, JD, Candidate Profile, options and renderDefaults, assigning generationId internally. The legacy stream retains caller-supplied generationId. No conversation context is accepted; there is no dependency on consumer TypeScript packages.

Repeated profile items have client-stable IDs. UUID5 combines generation ID, section kind and source ID, preserving structure when processing the same job.

Evidence is built only from Candidate Profile. Generated claims cite evidence IDs. JD and RAG guide relevance without establishing candidate facts.
