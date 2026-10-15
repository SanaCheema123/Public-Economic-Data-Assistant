from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.services.ai.base import AICompletion, AIProviderError
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.groq_provider import GroqProvider

logger = logging.getLogger("peda.ai")


class AIProviderManager:
    def __init__(self) -> None:
        self.providers = {"groq": GroqProvider(), "gemini": GeminiProvider()}

    def ordered_names(self) -> list[str]:
        primary = settings.ai_provider if settings.ai_provider in self.providers else "groq"
        secondary = "gemini" if primary == "groq" else "groq"
        return [primary, secondary]

    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> AICompletion:
        if settings.effective_ai_mode != "live":
            raise AIProviderError("External AI providers are disabled; deterministic grounded fallback is active")
        errors: list[str] = []
        for name in self.ordered_names():
            if name == "groq" and not settings.has_groq:
                continue
            if name == "gemini" and not settings.has_gemini:
                continue
            started = time.perf_counter()
            try:
                completion = await self.providers[name].complete(prompt, system=system, json_mode=json_mode)
                logger.info(
                    "ai_provider_success provider=%s latency_ms=%.2f json_mode=%s",
                    name, (time.perf_counter() - started) * 1000, json_mode,
                )
                return completion
            except AIProviderError as exc:
                # Never log prompts, API keys, or provider request bodies.
                logger.warning(
                    "ai_provider_failure provider=%s latency_ms=%.2f error_type=%s",
                    name, (time.perf_counter() - started) * 1000, type(exc).__name__,
                )
                errors.append(f"{name}: {exc}")
        raise AIProviderError("All configured AI providers failed. " + "; ".join(errors))


provider_manager = AIProviderManager()
