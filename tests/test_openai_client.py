from typing import Any, cast

import pytest

from outreach.ai.openai_client import OpenAIEmailGenerator


class FakeResponses:
    async def create(self, **kwargs):
        return type("FakeResponse", (), {"output_text": "not-json-with-sensitive-content"})()


class FakeClient:
    responses = FakeResponses()


@pytest.mark.asyncio
async def test_openai_invalid_json_error_is_sanitized() -> None:
    generator = cast(OpenAIEmailGenerator, object.__new__(OpenAIEmailGenerator))
    generator._client = cast(Any, FakeClient())
    generator._model = "test-model"

    with pytest.raises(ValueError) as exc_info:
        await generator.generate_email("system", "user")

    assert str(exc_info.value) == "OpenAI returned invalid email JSON."
    assert "sensitive" not in str(exc_info.value)
