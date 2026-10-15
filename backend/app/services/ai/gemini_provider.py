from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.ai.base import AICompletion, AIProvider, AIProviderError


class GeminiProvider(AIProvider):
    name = "gemini"

    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> AICompletion:
        if not settings.gemini_api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured")
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
        )
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1800},
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
                response = await client.post(endpoint, json=payload)
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            raise AIProviderError(f"Gemini request failed: {type(exc).__name__}") from exc
        try:
            content = body["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            raise AIProviderError("Gemini returned an unexpected response") from exc
        usage = body.get("usageMetadata") or {}
        return AICompletion(
            text=content,
            provider=self.name,
            input_tokens=int(usage.get("promptTokenCount") or 0),
            output_tokens=int(usage.get("candidatesTokenCount") or 0),
        )
