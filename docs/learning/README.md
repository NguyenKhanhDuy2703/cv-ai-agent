# Learning path: Generate CV Core Agent

This guide follows the production flow from request contract to saved canonical CV.

1. [System architecture](01-system-architecture.md)
2. [Generation workflow](02-agent-workflow.md)
3. [Contract and evidence](03-contract-evidence-generation.md)
4. [LLM provider and typed writers](04-llm-provider-and-prompting.md)
5. [RAG guidance](05-rag-fundamentals.md)
6. [Guardrails and evaluation](06-guardrails-and-evaluation.md)
7. [Render integration](07-render-integration.md)
8. [Implementation workbook](08-implementation-workbook.md)

After reading, you should be able to explain why the backend owns state, why candidate evidence is isolated from JD/RAG, how fallbacks produce a truthful partial result, and why validation happens before persistence.

Run the regression suite from the repository root with `python -m pytest -q`.
Canonical fixtures are stored locally in [tests/fixtures](../../tests/fixtures/README.md).
Shared factories live in `tests/helpers.py`; fixtures live in `tests/conftest.py`.
See [architecture snapshots](../../archify-architecture/README.md) for the diagrams
and their preserved source specifications.
