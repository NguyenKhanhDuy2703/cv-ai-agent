"""
Mock LLM provider for tests.

Returns a pre-configured response without making any network calls.
Configure responses per schema type via `set_response()`.

Usage in tests:
    mock = MockProvider()
    mock.set_response(RewriteResult, RewriteResult(
        path="experience[0].highlights[0]",
        text="Built microservice handling 10k req/s",
        source_ids=["leaf_0"],
    ))
    result = await mock.generate_structured(RewriteResult, messages)
    assert result.text == "Built microservice handling 10k req/s"
"""
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from . import GenerateOpts, LLMProvider, LLMSchemaError

T = TypeVar("T", bound=BaseModel)

# Sentinel to detect when no response has been configured
_MISSING = object()


class MockProvider:
    """
    Deterministic LLM provider for use in tests.
    No network, no API key required, zero cost.
    """

    def __init__(self) -> None:
        self._responses: dict[type, BaseModel] = {}
        self._call_log: list[dict] = []

    def set_response(self, schema: Type[T], response: T) -> None:
        """Register the response to return when schema is requested."""
        self._responses[schema] = response

    def call_log(self) -> list[dict]:
        """Return all recorded calls (schema name + messages)."""
        return list(self._call_log)

    async def generate_structured(
        self,
        schema: Type[T],
        messages: list[dict[str, str]],
        opts: Optional[GenerateOpts] = None,
    ) -> T:
        self._call_log.append({"schema": schema.__name__, "messages": messages})

        response = self._responses.get(schema, _MISSING)
        if response is _MISSING:
            raise LLMSchemaError(
                f"MockProvider has no configured response for schema '{schema.__name__}'. "
                "Call mock.set_response(schema, instance) in your test setup."
            )
        return response  # type: ignore[return-value]


# Verify MockProvider satisfies the LLMProvider protocol at import time
assert isinstance(MockProvider(), LLMProvider), "MockProvider must satisfy LLMProvider protocol"
