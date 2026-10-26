# 05 — RAG guidance

V1 uses `StaticKnowledgeRetriever` with lexical scoring and metadata filters for section, language, and industry. Each query returns at most five chunks.

RAG content contains writing rules and examples, not candidate history. Empty matches and retriever errors fall back to `NullKnowledgeRetriever`, allowing generation to continue without an external vector database.
