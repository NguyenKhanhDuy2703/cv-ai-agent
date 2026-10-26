"""
Static Knowledge Retriever using lexical token and phrase scoring over cleaned IT corpus.
"""
import math
import re
from typing import List, Optional, Set
from .retriever_protocol import KnowledgeChunk, KnowledgeRetriever, RetrievalRequest, RetrievalResult
from .corpus import IT_SOFTWARE_KNOWLEDGE_CHUNKS


def _tokenize(text: str) -> Set[str]:
    """Tokenize lowercased alphanumeric words of length >= 2."""
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9_#+]+", text.lower()))


class StaticKnowledgeRetriever(KnowledgeRetriever):
    def __init__(
        self,
        chunks: Optional[List[KnowledgeChunk]] = None,
        default_threshold: float = 0.1,
    ):
        self.chunks = chunks if chunks is not None else IT_SOFTWARE_KNOWLEDGE_CHUNKS
        self.default_threshold = default_threshold

    async def retrieve(
        self,
        request: RetrievalRequest,
        *,
        top_k: int = 5,
    ) -> RetrievalResult:
        query = (request.query or "").lower()
        keywords = [k.lower() for k in request.keywords]
        target_lang = (request.language or "vi").lower()
        target_industry = (request.industry or "it_software").lower()
        target_section = (request.section or "experience").lower()
        role_family = (request.role_family or "").lower()
        seniority = (request.seniority or "").lower()

        # Build full query token set
        query_tokens = _tokenize(query)
        for kw in keywords:
            query_tokens.update(_tokenize(kw))
        if role_family:
            query_tokens.update(_tokenize(role_family))
        if seniority:
            query_tokens.update(_tokenize(seniority))

        scored_chunks = []

        for chunk in self.chunks:
            # 1. Mandatory metadata filters
            if chunk.section != target_section:
                continue
            if chunk.industry != target_industry:
                continue
            # Language match: accept exact language or chunks marked "all"
            if chunk.language not in (target_lang, "all"):
                continue

            # 2. Lexical scoring
            chunk_title_tokens = _tokenize(chunk.title)
            chunk_content_tokens = _tokenize(chunk.content)
            chunk_category_tokens = _tokenize(chunk.category)
            chunk_id_tokens = _tokenize(chunk.id)

            score = 0.0

            # Title matches (weight = 3.0)
            title_overlap = query_tokens & chunk_title_tokens
            score += len(title_overlap) * 3.0

            # Category matches (weight = 2.0)
            cat_overlap = query_tokens & chunk_category_tokens
            score += len(cat_overlap) * 2.0

            # ID matches (weight = 2.0)
            id_overlap = query_tokens & chunk_id_tokens
            score += len(id_overlap) * 2.0

            # Content matches (weight = 1.0)
            content_overlap = query_tokens & chunk_content_tokens
            score += len(content_overlap) * 1.0

            # Direct phrase bonus
            if chunk.category in query:
                score += 2.0
            if chunk.id.replace("it-rule-", "").replace("-", " ") in query:
                score += 3.0

            if score >= self.default_threshold:
                # Normalize score
                normalized_score = min(1.0, score / 15.0)
                chunk_copy = chunk.model_copy(update={"score": round(normalized_score, 3)})
                scored_chunks.append((score, chunk_copy))

        # Sort descending by raw score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = [item[1] for item in scored_chunks[:top_k]]

        return RetrievalResult(
            chunks=top_chunks,
            total_found=len(scored_chunks),
            retriever_name="StaticKnowledgeRetriever",
        )
