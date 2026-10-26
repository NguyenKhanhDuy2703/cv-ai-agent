# 03 — Contract and evidence

TypeScript contracts live in `packages/cv-contracts/src/ai.ts`; Python mirrors them in `src/schemas/generation.py`. A request includes requestId, generationId, JD, Candidate Profile, options and Render defaults. It accepts no conversation context.

Repeated profile items have client-stable IDs. UUID5 combines generation ID, section kind and source ID, preserving structure when processing the same job.

Evidence is built only from Candidate Profile. Generated claims cite evidence IDs. JD and RAG guide relevance without establishing candidate facts.
