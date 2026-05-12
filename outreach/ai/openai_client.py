"""OpenAI email generation client."""

from __future__ import annotations

import json
from typing import Any

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, InternalServerError, RateLimitError
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from outreach.models import GeneratedEmail


EMAIL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "personalization_notes": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["subject", "body", "personalization_notes", "confidence", "warnings"],
}


class OpenAIEmailGenerator:
    """Generate structured outreach emails with OpenAI."""

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(
            (TimeoutError, ConnectionError, APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)
        ),
        reraise=True,
    )
    async def generate_email(self, system_prompt: str, user_prompt: str) -> GeneratedEmail:
        """Call OpenAI and parse the strict JSON response."""
        response = await self._client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "outreach_email",
                    "schema": EMAIL_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw_text = getattr(response, "output_text", None)
        if not raw_text:
            raw_text = self._extract_text(response)
        try:
            payload = json.loads(raw_text)
            return GeneratedEmail.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError("OpenAI returned invalid email JSON.") from exc

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Best-effort extraction for SDK response objects."""
        chunks: list[str] = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
        return "\n".join(chunks)
