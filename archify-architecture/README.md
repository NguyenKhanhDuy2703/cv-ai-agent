# Architecture Snapshots

Open [index.html](index.html) to browse the interactive **Archify Portal Dashboard** for all 5 diagrams.
Each HTML file is self-contained with zero CDN dependencies; the index loads diagrams using relative paths.

| Published Diagram | Type | Preserved Source Specification | Description |
| --- | --- | --- | --- |
| [System Architecture](cv-system.html) | Architecture | [cv-system.json](specs/cv-system.json) | Stateless system topology across FastAPI Gateway, Generation Pipeline, Candidate Evidence Store, Deterministic Guards, Static RAG, and LLM Provider. |
| [Generation Pipeline](cv-pipeline.html) | Workflow | [cv-pipeline.json](specs/cv-pipeline.json) | 8-step one-shot generation pipeline (Gap Detection, Evidence Isolation, JD Analysis, Static RAG, Section Writers, 0% Fabrication Guard, and RenderCV Validation). |
| [SSE Sequence](cv-sequence.html) | Sequence | [cv-sequence.json](specs/cv-sequence.json) | Real-time SSE streaming lifecycle: Service Bearer auth, asyncio queue buffering, guarded section generation, and terminal `done`/`needs_input` delivery. |
| [API Subsystem Flow](cv-api.html) | Architecture | [cv-api.json](specs/cv-api.json) | Server bootstrap (`main.py`), CORS + 10MB body limit, `POST /v1/ai/generate/stream` routing, and `GenerateService` lifecycle. |
| [Codebase Hierarchy](cv-modules.html) | Tree | [cv-modules.json](specs/cv-modules.json) | Module tree decomposition across `src/` (`api`, `constants`, `core`, `guard`, `knowledge`, `llm`, `pipeline/generation`, `schemas`, `yaml_layer`). |

The five specifications are pinned to the latest Git commit (`f37d777ff952b9b453d70b1f843de01fa7aa0a53`) and verified against repository evidence. Intermediate renders, receipts, and browser logs are disposable.

See the [project README](../README.md) and [learning guide](../docs/learning/README.md) for the one-shot generation contract and test execution.
