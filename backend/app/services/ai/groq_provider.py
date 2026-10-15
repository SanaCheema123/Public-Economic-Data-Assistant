from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.ai.base import AICompletion, AIProvider, AIProviderError


class GroqProvider(AIProvider):
    name = "groq"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> AICompletion:
        if not settings.groq_api_key:
            raise AIProviderError("GROQ_API_KEY is not configured")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": settings.groq_model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1800,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            raise AIProviderError(f"Groq request failed: {type(exc).__name__}") from exc
        usage = body.get("usage") or {}
        try:
            content = body["choices"][0]["message"]["content"]
        except Exception as exc:
            raise AIProviderError("Groq returned an unexpected response") from exc
        return AICompletion(
            text=content,
            provider=self.name,
            input_tokens=int(usage.get("prompt_tokens") or 0),
            output_tokens=int(usage.get("completion_tokens") or 0),
        )
