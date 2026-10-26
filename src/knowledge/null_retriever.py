"""
NullKnowledgeRetriever: Safe default when RAG is disabled or knowledge is unavailable.
Guarantees Agent Core runs purely on Candidate Evidence + JD with zero external dependency.
"""
from .retriever_protocol import KnowledgeRetriever, RetrievalRequest, RetrievalResult


class NullKnowledgeRetriever(KnowledgeRetriever):
    """Returns an empty result immediately. Allows pipeline to execute with RAG off."""

    async def retrieve(
        self,
        request: RetrievalRequest,
        *,
        top_k: int = 5,
    ) -> RetrievalResult:
        return RetrievalResult(
            chunks=[],
            total_found=0,
            retriever_name="NullKnowledgeRetriever",
        )
