"""
Knowledge Retrieval Protocol and DTOs.
Defines the unified retrieval contract for Agent Core (NullRetriever, StaticRetriever, and VectorRetriever).
"""
from typing import Any, List, Optional, Protocol
from pydantic import BaseModel, Field


class KnowledgeChunk(BaseModel):
    id: str = Field(..., description="Unique chunk / rule ID")
    title: str = Field(default="", description="Rule or guide title")
    content: str = Field(..., description="Guidance rule text (non-factual writing rule)")
    category: str = Field(default="writing_rule", description="Category: writing_rule | formula | action_verb | metric_tip")
    industry: str = Field(default="it_software", description="Target industry")
    section: str = Field(default="experience", description="Target CV section")
    language: str = Field(default="vi", description="Language: vi or en")
    source: str = Field(default="RenderCV Best Practices", description="Attribution / source")
    version: str = Field(default="1.0", description="Rule version")
    score: float = Field(default=0.0, description="Relevance score (0.0 to 1.0)")


class RetrievalRequest(BaseModel):
    query: str = Field(default="", description="Query string or JD snippet")
    section: str = Field(default="experience", description="Target section")
    industry: str = Field(default="it_software", description="Target industry")
    language: str = Field(default="vi", description="Target language")
    seniority: Optional[str] = Field(default=None, description="Seniority level")
    role_family: Optional[str] = Field(default=None, description="Role family")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords")


class RetrievalResult(BaseModel):
    chunks: List[KnowledgeChunk] = Field(default_factory=list)
    total_found: int = 0
    retriever_name: str = "NullKnowledgeRetriever"


class KnowledgeRetriever(Protocol):
    """Protocol for all knowledge retrievers."""

    async def retrieve(
        self,
        request: RetrievalRequest,
        *,
        top_k: int = 5,
    ) -> RetrievalResult:
        ...
