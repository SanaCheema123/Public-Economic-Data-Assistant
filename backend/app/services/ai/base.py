from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class AIProviderError(RuntimeError):
    pass


@dataclass
class AICompletion:
    text: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0

    def json(self) -> dict[str, Any]:
        text = self.text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lstrip().startswith("json"):
                text = text.lstrip()[4:].lstrip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        return json.loads(text)


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, prompt: str, system: str | None = None, json_mode: bool = False) -> AICompletion:
        raise NotImplementedError
