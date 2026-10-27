# Glossary

## Candidate Profile
The complete user-supplied fact snapshot used to generate a CV.

## Candidate evidence
Stable, traceable facts extracted only from Candidate Profile.

## JD analysis
Target-role structure and keywords derived from the job description. It guides relevance but is not personal evidence.

## RAG guidance
Writing guidance retrieved by section, locale, and industry. It is never a factual source about the candidate.

## Gap
A missing required or recommended input. Required gaps stop writers and return `needs_input`.

## Typed writer
An LLM call constrained to a Pydantic/Zod-compatible output with evidence IDs.

## Deterministic guard
Code that rejects unsupported claims, metrics, dates, companies, titles, skills, or certifications.

## Canonical document
The validated RenderCV object containing `cv`, `design`, `locale`, and `settings`.

## Stable ID
A deterministic UUID based on generation and client item identity.

## Generation job
An AI-owned durable record containing an immutable input snapshot, request ID, status, deadline, attempts, lease, persisted events and validated result. Each job has one persisted terminal outcome. Consumer CV IDs belong to the consuming backend.

## Partial result
A valid CV produced with source-fact fallbacks and warnings after a non-fatal writer or retrieval problem.
