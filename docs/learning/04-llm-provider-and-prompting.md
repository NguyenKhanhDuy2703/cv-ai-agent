# 04 — LLM provider and typed writers

All model calls use `LLMProvider.generate_structured(schema, messages)`. Provider failures are classified centrally and writers own deterministic fallbacks.

Typed writers generate only content:

- Summary returns text plus evidence IDs.
- Experience returns indexed bullets plus evidence IDs.
- Projects return source ID, highlights, and evidence IDs.

Contact, Education, Certifications, Achievements, and Languages are copied by code. Skills are selected only from the supplied skill list. Prompts clearly label JD/RAG as targeting guidance rather than candidate facts.
