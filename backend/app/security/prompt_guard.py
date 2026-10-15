from __future__ import annotations

import re

_PATTERNS = [
    r"ignore (all|any|the|your) (previous|prior|system) instructions",
    r"reveal (the )?(system prompt|api key|secret|password|jwt)",
    r"unrestricted database access",
    r"bypass (sql|security|citation|authentication)",
    r"developer message",
    r"drop\s+table",
]


def detect_prompt_injection(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(re.search(pattern, normalized) for pattern in _PATTERNS)


def sanitize_user_text(text: str, max_length: int = 4000) -> str:
    text = text.replace("\x00", "").strip()
    if len(text) > max_length:
        raise ValueError(f"Input exceeds {max_length} characters")
    return text
