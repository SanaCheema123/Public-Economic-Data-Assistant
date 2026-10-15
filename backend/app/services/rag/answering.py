from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.services.ai import AIProviderError, provider_manager


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "ar" if arabic > latin else "en"


def classify_intent(text: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["define", "definition", "what does", "explain indicator"]) or any(k in text for k in ["عرّف", "تعريف", "ماذا يعني"]):
        return "definition"
    if any(k in lowered for k in ["compare", "versus", " vs "]) or "قارن" in text:
        return "comparison"
    if any(k in lowered for k in ["trend", "over time", "last "]) or any(k in text for k in ["اتجاه", "خلال", "آخر"]):
        return "timeseries"
    return "statistic"


def _fmt_value(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.1f}"
    if float(value).is_integer():
        return f"{value:.0f}"
    return f"{value:.1f}"


def deterministic_answers(rows: list[dict[str, Any]], language: str, intent: str) -> tuple[str, str]:
    if not rows:
        return (
            "I couldn't find a verified dataset for this indicator in the currently available sources.",
            "لم أتمكن من العثور على مجموعة بيانات موثوقة لهذا المؤشر ضمن المصادر المتاحة حالياً.",
        )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("indicator_name")), []).append(row)
    en_parts: list[str] = []
    ar_parts: list[str] = []
    for _, group in grouped.items():
        ordered = sorted(group, key=lambda r: (str(r.get("date")), str(r.get("region") or ""), str(r.get("sector") or "")))
        latest = ordered[-1]
        name_en = str(latest.get("indicator_name") or "Indicator")
        name_ar = str(latest.get("indicator_name_ar") or "المؤشر")
        unit = str(latest.get("unit") or "")
        if latest.get("region") or latest.get("sector"):
            en_parts.append(f"{name_en} is available as a categorical breakdown with {len(ordered)} reported entries in the selected period.")
            ar_parts.append(f"يتوفر {name_ar} كتوزيع فئوي يضم {len(ordered)} قيماً ضمن الفترة المحددة.")
            continue
        year = str(latest.get("date"))[:4]
        value = _fmt_value(float(latest["value"]))
        if len(ordered) == 1:
            en_parts.append(f"{name_en} is {value}{unit if unit.startswith('%') else (' ' + unit if unit else '')} for {year}.")
            ar_parts.append(f"بلغ {name_ar} {value}{unit if unit.startswith('%') else (' ' + unit if unit else '')} في عام {year}.")
        else:
            first = ordered[0]
            first_value = float(first["value"])
            last_value = float(latest["value"])
            direction = "increased" if last_value > first_value else "decreased" if last_value < first_value else "was unchanged"
            direction_ar = "ارتفع" if last_value > first_value else "انخفض" if last_value < first_value else "لم يتغير"
            en_parts.append(f"{name_en} {direction} from {_fmt_value(first_value)} to {value}{unit if unit.startswith('%') else (' ' + unit if unit else '')} between {str(first.get('date'))[:4]} and {year}.")
            ar_parts.append(f"{direction_ar} {name_ar} من {_fmt_value(first_value)} إلى {value}{unit if unit.startswith('%') else (' ' + unit if unit else '')} بين عامي {str(first.get('date'))[:4]} و{year}.")
    return (" ".join(en_parts), " ".join(ar_parts))


async def generate_answers(question: str, rows: list[dict[str, Any]], intent: str, language: str) -> tuple[str, str, str]:
    fallback_en, fallback_ar = deterministic_answers(rows, language, intent)
    if not rows or settings.effective_ai_mode != "live":
        return fallback_en, fallback_ar, "deterministic"
    safe_rows = [
        {k: (str(v) if k == "date" else v) for k, v in row.items() if k in {
            "indicator_name", "indicator_name_ar", "unit", "date", "value", "region", "sector",
            "dataset_name", "dataset_name_ar", "source_name", "source_name_ar", "verification_status",
            "dataset_verification_status",
        }}
        for row in rows[:100]
    ]
    system = """You are the Public Economic Data Assistant. Answer only from DATA_CONTEXT below. Never use model memory for factual statistics. Never invent a value, source, dataset, date, or citation. If context is insufficient, say verified data is unavailable. Produce concise bilingual output as JSON with answer_en and answer_ar."""
    prompt = json.dumps({"question": question, "intent": intent, "data_context": safe_rows}, ensure_ascii=False, default=str)
    try:
        completion = await provider_manager.complete(prompt, system=system, json_mode=True)
        payload = completion.json()
        en = str(payload.get("answer_en") or fallback_en)
        ar = str(payload.get("answer_ar") or fallback_ar)
        return en, ar, completion.provider
    except (AIProviderError, ValueError, json.JSONDecodeError):
        return fallback_en, fallback_ar, "deterministic"
