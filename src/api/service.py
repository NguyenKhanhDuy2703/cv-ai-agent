"""Stateless AI stream consumed by the backend worker, not browser subscribers."""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

from ..knowledge.retriever_protocol import KnowledgeRetriever
from ..config import settings
from ..llm import LLMProvider
from ..llm.factory import get_llm_provider
from ..pipeline.generation import CvGenerationPipeline
from ..schemas.generation import GenerateCvRequest

logger = logging.getLogger(__name__)


class GenerateService:
    def __init__(self, provider: Optional[LLMProvider] = None, retriever: Optional[KnowledgeRetriever] = None):
        configured_provider = provider
        if configured_provider is None and settings.ai_provider != "mock":
            configured_provider = get_llm_provider()
        self.pipeline = CvGenerationPipeline(provider=configured_provider, retriever=retriever)

    async def stream(
        self, request: GenerateCvRequest,
    ) -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        sequence = 0

        async def on_event(event: Dict[str, Any]) -> None:
            await queue.put(event)

        task = asyncio.create_task(self.pipeline.generate(request, on_event=on_event))
        try:
            while not task.done() or not queue.empty():
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                sequence += 1
                event_type = item["type"]
                envelope = {
                    "type": event_type,
                    "requestId": request.request_id,
                    "generationId": request.generation_id,
                    "sequence": sequence,
                    "data": item["data"],
                }
                yield f"event: {event_type}\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"

            result = await task
            sequence += 1
            terminal = "needs_input" if result.status == "needs_input" else (
                "error" if result.status == "failed" else "done"
            )
            envelope = {
                "type": terminal,
                "requestId": request.request_id,
                "generationId": request.generation_id,
                "sequence": sequence,
                "data": {"message": "Generation failed"} if terminal == "error" else result.model_dump(by_alias=True),
            }
            yield f"event: {terminal}\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            raise
        except Exception as exc:
            logger.exception("CV generation failed requestId=%s", request.request_id)
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            sequence += 1
            envelope = {
                "type": "error",
                "requestId": request.request_id,
                "generationId": request.generation_id,
                "sequence": sequence,
                "data": {"message": str(exc)},
            }
            yield f"event: error\ndata: {json.dumps(envelope, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
