from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.rag.sql_validator import SQLValidationResult, validate_sql
from app.services.rag.text_to_sql import SQLPlan, correct_sql_plan
from app.services.rag.retrieval import RetrievedIndicator


@dataclass
class SQLExecution:
    rows: list[dict[str, Any]]
    sql: str
    params: dict[str, Any]
    elapsed_ms: int


class UnsafeSQL(ValueError):
    pass


class QueryExecutionError(RuntimeError):
    pass


async def validate_and_execute(
    db: Session,
    plan: SQLPlan,
    question: str,
    retrieved: list[RetrievedIndicator],
) -> SQLExecution:
    validation = validate_sql(plan.sql, plan.params)
    if not validation.valid:
        corrected = await correct_sql_plan(question, plan, validation.errors, retrieved)
        validation = validate_sql(corrected.sql, corrected.params)
    if not validation.valid:
        raise UnsafeSQL("; ".join(validation.errors))

    started = time.perf_counter()
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            db.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": str(settings.sql_timeout_ms)},
            )
        result = db.execute(text(validation.sql), validation.params)
        rows = [dict(row) for row in result.mappings().all()]
    except SQLAlchemyError as exc:
        db.rollback()
        raise QueryExecutionError("The verified data query could not be executed safely.") from exc
    elapsed = int((time.perf_counter() - started) * 1000)
    return SQLExecution(rows=rows, sql=validation.sql, params=validation.params, elapsed_ms=elapsed)
