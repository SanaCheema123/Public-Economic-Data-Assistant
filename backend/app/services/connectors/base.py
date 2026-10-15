from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConnectorResult:
    ok: bool
    source: str
    records: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class BaseDataConnector(ABC):
    source_slug: str

    @abstractmethod
    async def fetch(self, **kwargs) -> ConnectorResult:
        raise NotImplementedError
