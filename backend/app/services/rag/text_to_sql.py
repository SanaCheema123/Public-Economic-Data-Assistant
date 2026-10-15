from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.ai import AIProviderError, provider_manager
from app.services.rag.retrieval import RetrievedIndicator


@dataclass
class SQLPlan:
    sql: str
    params: dict[str, Any]
    chart_hint: str
    explanation: str
    provider: str = "deterministic"


def _extract_year(question: str) -> int | None:
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", question)
    return int(years[-1]) if years else None


def _extract_last_years(question: str) -> int | None:
    match = re.search(r"last\s+(\d{1,2})\s+years?", question.lower())
    if match:
        return min(max(int(match.group(1)), 1), 30)
    arabic = re.search(r"(?:آخر|خلال)\s+(\d{1,2})\s+(?:سنوات|سنة)", question)
    if arabic:
        return min(max(int(arabic.group(1)), 1), 30)
    return None


def deterministic_plan(question: str, retrieved: list[RetrievedIndicator]) -> SQLPlan:
    if not retrieved:
        raise ValueError("No indicator available for SQL planning")
    comparison = any(term in question.lower() for term in ["compare", "comparison", " versus ", " vs "]) or "قارن" in question
    selected = retrieved[:2] if comparison and len(retrieved) > 1 else retrieved[:1]
    clauses = []
    params: dict[str, Any] = {"row_limit": settings.sql_row_limit}
    for idx, item in enumerate(selected):
        key = f"indicator_{idx}"
        params[key] = item.indicator.id
        clauses.append(f"i.id = :{key}")
    where = "(" + " OR ".join(clauses) + ")"

    year = _extract_year(question)
    last_years = _extract_last_years(question)
    if year:
        where += " AND iv.date >= :year_start AND iv.date < :year_end"
        params["year_start"] = f"{year:04d}-01-01"
        params["year_end"] = f"{year + 1:04d}-01-01"
    # For "last N years" we intentionally retrieve the bounded indicator series and
    # apply the data-relative window after execution. This stays portable between
    # PostgreSQL and the SQLite test fallback.

    sql = f"""
        SELECT
            i.id AS indicator_uuid,
            i.indicator_id,
            i.name_en AS indicator_name,
            i.name_ar AS indicator_name_ar,
            i.unit,
            i.category,
            i.verification_status,
            iv.date,
            iv.value,
            iv.region,
            iv.sector,
            d.id AS dataset_id,
            d.name_en AS dataset_name,
            d.name_ar AS dataset_name_ar,
            d.source_url AS dataset_url,
            d.verification_status AS dataset_verification_status,
            s.id AS source_id,
            s.name_en AS source_name,
            s.name_ar AS source_name_ar,
            s.url AS source_url
        FROM indicator_values iv
        JOIN indicators i ON i.id = iv.indicator_id
        JOIN datasets d ON d.id = i.dataset_id
        JOIN sources s ON s.id = i.source_id
        WHERE {where}
        ORDER BY i.name_en, iv.date, iv.region, iv.sector
        LIMIT :row_limit
    """
    if any(item.indicator.category == "Regional" for item in selected):
        chart_hint = "donut"
    elif comparison:
        chart_hint = "grouped_bar"
    elif year and selected[0].indicator.category != "Population":
        chart_hint = "bar"
    else:
        chart_hint = "line"
    return SQLPlan(sql=" ".join(sql.split()), params=params, chart_hint=chart_hint, explanation="Deterministic safe query plan")


async def generate_sql_plan(question: str, retrieved: list[RetrievedIndicator], language: str) -> SQLPlan:
    if settings.effective_ai_mode != "live":
        return deterministic_plan(question, retrieved)
    indicator_context = [
        {
            "id": item.indicator.id,
            "indicator_id": item.indicator.indicator_id,
            "name_en": item.indicator.name_en,
            "name_ar": item.indicator.name_ar,
            "unit": item.indicator.unit,
            "category": item.indicator.category,
        }
        for item in retrieved[:5]
    ]
    system = """You are a read-only PostgreSQL query planner for a public economic data assistant.
Return JSON only with keys sql, params, chart_hint, explanation.
Rules: generate exactly one SELECT or WITH...SELECT query; use only indicator_values iv, indicators i, datasets d, sources s, data_dimensions dd; use named parameters like :year; never interpolate user text; never use INSERT/UPDATE/DELETE/DDL/COPY/system catalogs; include joins needed for source and dataset metadata; always include LIMIT :row_limit; row_limit is 200; use only the supplied indicator UUIDs; do not invent tables, columns, sources or statistics."""
    prompt = f"Question ({language}): {question}\nAvailable indicators:\n{json.dumps(indicator_context, ensure_ascii=False)}"
    try:
        completion = await provider_manager.complete(prompt, system=system, json_mode=True)
        payload = completion.json()
        return SQLPlan(
            sql=str(payload["sql"]),
            params={**dict(payload.get("params") or {}), "row_limit": settings.sql_row_limit},
            chart_hint=str(payload.get("chart_hint") or "line"),
            explanation=str(payload.get("explanation") or "AI generated query plan"),
            provider=completion.provider,
        )
    except (AIProviderError, KeyError, ValueError, json.JSONDecodeError):
        return deterministic_plan(question, retrieved)

async def correct_sql_plan(question: str, plan: SQLPlan, errors: list[str], retrieved: list[RetrievedIndicator]) -> SQLPlan:
    """One bounded correction attempt. Falls back to deterministic planning on any failure."""
    if settings.effective_ai_mode != "live" or plan.provider == "deterministic":
        return deterministic_plan(question, retrieved)
    system = """Correct a read-only PostgreSQL SELECT query. Return JSON only: sql, params, chart_hint, explanation.
Use only indicator_values iv, indicators i, datasets d, sources s, data_dimensions dd. Use named parameters. Never use DML/DDL/COPY/system catalogs. Always LIMIT :row_limit. Do not invent schema elements."""
    context = [{"id": r.indicator.id, "name": r.indicator.name_en} for r in retrieved[:5]]
    prompt = json.dumps({
        "question": question,
        "invalid_sql": plan.sql,
        "params": plan.params,
        "validator_errors": errors,
        "allowed_indicators": context,
    }, ensure_ascii=False)
    try:
        completion = await provider_manager.complete(prompt, system=system, json_mode=True)
        payload = completion.json()
        return SQLPlan(
            sql=str(payload["sql"]),
            params={**dict(payload.get("params") or {}), "row_limit": settings.sql_row_limit},
            chart_hint=str(payload.get("chart_hint") or plan.chart_hint),
            explanation=str(payload.get("explanation") or "Corrected query plan"),
            provider=completion.provider,
        )
    except Exception:
        return deterministic_plan(question, retrieved)
