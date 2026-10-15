from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, TypedDict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.common import ChartSpec, CitationOut
from app.security.prompt_guard import detect_prompt_injection
from app.services.rag.answering import classify_intent, detect_language, generate_answers
from app.services.rag.charting import build_chart
from app.services.rag.citations import build_citations
from app.services.rag.retrieval import RetrievedIndicator, retriever
from app.services.rag.sql_validator import validate_sql
from app.services.rag.text_to_sql import SQLPlan, correct_sql_plan, generate_sql_plan

try:  # Installed in the production Docker image.
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover
    END = START = None
    StateGraph = None


class AssistantState(TypedDict, total=False):
    db: Session
    question: str
    requested_language: str | None
    language: str
    intent: str
    blocked: bool
    block_reason: str
    retrieved: list[RetrievedIndicator]
    definitions: list[str]
    source_context: list[dict[str, Any]]
    query_type: str
    sql_plan: SQLPlan
    validated_sql: str
    validated_params: dict[str, Any]
    validation_errors: list[str]
    rows: list[dict[str, Any]]
    analysis: dict[str, Any]
    chart: ChartSpec | None
    answer_en: str
    answer_ar: str
    answer_provider: str
    citations: list[CitationOut]
    confidence: str
    unsupported: bool
    final: dict[str, Any]


def _blocked(state: AssistantState) -> bool:
    return bool(state.get("blocked"))


def _requested_last_years(question: str) -> int | None:
    lowered = question.lower()
    match = re.search(r"last\s+(\d{1,2})\s+years?", lowered)
    if match:
        return min(max(int(match.group(1)), 1), 30)
    words = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
    for word, value in words.items():
        if re.search(rf"last\s+{word}\s+years?", lowered):
            return value
    arabic_digits = re.search(r"(?:آخر|اخر|خلال)\s+(\d{1,2})\s+(?:سنوات|سنة)", question)
    if arabic_digits:
        return min(max(int(arabic_digits.group(1)), 1), 30)
    arabic_words = {"سنة":1,"سنتين":2,"ثلاث":3,"ثلاثة":3,"أربع":4,"اربعة":4,"أربعة":4,"خمس":5,"خمسة":5,"ست":6,"سبع":7,"ثمان":8,"تسع":9,"عشر":10}
    for word, value in arabic_words.items():
        if word in question and any(prefix in question for prefix in ["آخر", "اخر", "خلال"]):
            return value
    return None


def _has_explicit_year(question: str) -> bool:
    return bool(re.search(r"\b(?:19|20)\d{2}\b", question))


def _scope_rows(rows: list[dict[str, Any]], question: str, intent: str) -> list[dict[str, Any]]:
    if not rows:
        return rows
    n = _requested_last_years(question)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = str(row.get("indicator_uuid") or row.get("indicator_id") or "indicator")
        grouped.setdefault(key, []).append(row)
    output: list[dict[str, Any]] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda row: str(row.get("date") or ""))
        if n:
            output.extend(ordered[-n:])
        elif intent in {"statistic", "comparison"} and not _has_explicit_year(question):
            output.append(ordered[-1])
        else:
            output.extend(ordered)
    return output


async def detect_language_node(state: AssistantState) -> AssistantState:
    question = state["question"]
    blocked = detect_prompt_injection(question)
    return {
        "language": state.get("requested_language") or detect_language(question),
        "blocked": blocked,
        "block_reason": "The request attempts to bypass protected system capabilities." if blocked else "",
    }


async def classify_intent_node(state: AssistantState) -> AssistantState:
    if _blocked(state):
        return {}
    return {"intent": classify_intent(state["question"])}


async def retrieve_indicators_node(state: AssistantState) -> AssistantState:
    if _blocked(state):
        return {"retrieved": []}
    items = retriever.retrieve_indicators(state["db"], state["question"], limit=5)
    return {"retrieved": items}


async def retrieve_definitions_node(state: AssistantState) -> AssistantState:
    if _blocked(state):
        return {"definitions": []}
    language = state.get("language", "en")
    return {"definitions": [retriever.retrieve_definition(item.indicator, language) for item in state.get("retrieved", [])]}


async def retrieve_sources_node(state: AssistantState) -> AssistantState:
    context = []
    for item in state.get("retrieved", []):
        context.append({
            "id": item.source.id,
            "name_en": item.source.name_en,
            "name_ar": item.source.name_ar,
            "url": item.source.url,
            "dataset_id": item.dataset.id,
            "dataset_name_en": item.dataset.name_en,
            "dataset_name_ar": item.dataset.name_ar,
            "verification_status": item.dataset.verification_status,
        })
    return {"source_context": context}


async def determine_query_type_node(state: AssistantState) -> AssistantState:
    if _blocked(state) or not state.get("retrieved"):
        return {"query_type": "unsupported"}
    if state.get("intent") == "definition":
        return {"query_type": "metadata"}
    return {"query_type": "sql"}


async def generate_sql_node(state: AssistantState) -> AssistantState:
    if state.get("query_type") != "sql":
        return {}
    plan = await generate_sql_plan(state["question"], state["retrieved"], state.get("language", "en"))
    return {"sql_plan": plan}


async def validate_sql_node(state: AssistantState) -> AssistantState:
    if state.get("query_type") != "sql":
        return {}
    plan = state["sql_plan"]
    validation = validate_sql(plan.sql, plan.params)
    allowed_indicator_ids = {item.indicator.id for item in state.get("retrieved", [])}
    def scope_errors(candidate: SQLPlan) -> list[str]:
        sql_lower = candidate.sql.lower()
        param_values = {str(v) for v in candidate.params.values()}
        errors: list[str] = []
        if not (("i.id" in sql_lower) or ("iv.indicator_id" in sql_lower)):
            errors.append("Assistant SQL must explicitly scope the query to retrieved indicators")
        if allowed_indicator_ids and not (param_values & allowed_indicator_ids):
            errors.append("Assistant SQL does not reference an approved retrieved indicator")
        uuid_like = {v for v in param_values if re.fullmatch(r"[0-9a-fA-F-]{36}", v)}
        if uuid_like - allowed_indicator_ids:
            errors.append("Assistant SQL references an unapproved indicator UUID")
        return errors

    combined_errors = list(validation.errors) + scope_errors(plan)
    if combined_errors:
        corrected = await correct_sql_plan(state["question"], plan, combined_errors, state["retrieved"])
        validation = validate_sql(corrected.sql, corrected.params)
        plan = corrected
        combined_errors = list(validation.errors) + scope_errors(plan)
    return {
        "sql_plan": plan,
        "validated_sql": validation.sql if validation.valid and not combined_errors else "",
        "validated_params": validation.params if validation.valid and not combined_errors else {},
        "validation_errors": combined_errors,
    }


async def execute_sql_node(state: AssistantState) -> AssistantState:
    if state.get("query_type") != "sql" or state.get("validation_errors"):
        return {"rows": []}
    db = state["db"]
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            db.execute(
                text("SELECT set_config('statement_timeout', :timeout, true)"),
                {"timeout": str(settings.sql_timeout_ms)},
            )
        rows = [dict(row) for row in db.execute(text(state["validated_sql"]), state["validated_params"]).mappings().all()]
        rows = _scope_rows(rows, state["question"], state.get("intent", "statistic"))
        return {"rows": rows}
    except Exception:
        db.rollback()
        return {"rows": [], "validation_errors": ["Safe SQL execution failed"]}


async def analyze_result_node(state: AssistantState) -> AssistantState:
    rows = state.get("rows", [])
    if state.get("query_type") == "metadata":
        return {"analysis": {"row_count": 0, "metadata_only": True}}
    return {"analysis": {"row_count": len(rows), "metadata_only": False}}


async def generate_chart_node(state: AssistantState) -> AssistantState:
    if state.get("query_type") != "sql" or not state.get("rows"):
        return {"chart": None}
    hint = state.get("sql_plan").chart_hint if state.get("sql_plan") else "line"
    return {"chart": build_chart(state["rows"], hint, state.get("language", "en"))}


async def generate_answer_node(state: AssistantState) -> AssistantState:
    if _blocked(state):
        return {
            "answer_en": "I can help with public economic data, but I can't bypass database, citation, authentication, or system safety controls.",
            "answer_ar": "يمكنني المساعدة في البيانات الاقتصادية العامة، لكن لا يمكنني تجاوز ضوابط قاعدة البيانات أو الاستشهادات أو المصادقة أو أمان النظام.",
            "answer_provider": "safety",
        }
    if not state.get("retrieved"):
        return {
            "answer_en": "I couldn't find a verified dataset for this indicator in the currently available sources.",
            "answer_ar": "لم أتمكن من العثور على مجموعة بيانات موثوقة لهذا المؤشر ضمن المصادر المتاحة حالياً.",
            "answer_provider": "unsupported",
        }
    if state.get("query_type") == "metadata":
        item = state["retrieved"][0]
        return {
            "answer_en": f"{item.indicator.name_en}: {item.indicator.description_en}",
            "answer_ar": f"{item.indicator.name_ar}: {item.indicator.description_ar}",
            "answer_provider": "retrieval",
        }
    if state.get("validation_errors") or not state.get("rows"):
        return {
            "answer_en": "I found a relevant indicator, but I couldn't produce a safe verified query result. No statistic has been guessed.",
            "answer_ar": "عثرت على مؤشر ذي صلة، لكن تعذر إنتاج نتيجة استعلام آمنة وموثوقة. لم يتم تخمين أي قيمة إحصائية.",
            "answer_provider": "safety",
        }
    en, ar, provider = await generate_answers(state["question"], state["rows"], state.get("intent", "statistic"), state.get("language", "en"))
    return {"answer_en": en, "answer_ar": ar, "answer_provider": provider}


async def attach_citations_node(state: AssistantState) -> AssistantState:
    if _blocked(state) or not state.get("retrieved"):
        return {"citations": []}
    if state.get("query_type") == "sql" and state.get("rows"):
        return {"citations": build_citations(state["rows"])}
    item = state["retrieved"][0]
    citation = CitationOut(
        title=f"{item.indicator.name_en} — {item.dataset.name_en}",
        source_name=item.source.name_en,
        source_name_ar=item.source.name_ar,
        dataset_name=item.dataset.name_en,
        dataset_name_ar=item.dataset.name_ar,
        indicator_name=item.indicator.name_en,
        indicator_name_ar=item.indicator.name_ar,
        period=None,
        url=item.dataset.source_url or item.source.url,
        verification_status=item.dataset.verification_status,
    )
    return {"citations": [citation]}


async def safety_check_node(state: AssistantState) -> AssistantState:
    unsupported = bool(
        _blocked(state)
        or not state.get("retrieved")
        or (state.get("query_type") == "sql" and (state.get("validation_errors") or not state.get("rows")))
    )
    citations = state.get("citations", [])
    if state.get("query_type") in {"sql", "metadata"} and not unsupported and not citations:
        unsupported = True
    confidence = "unsupported" if unsupported else "high"
    return {"unsupported": unsupported, "confidence": confidence}


async def final_response_node(state: AssistantState) -> AssistantState:
    return {"final": {
        "answer_en": state.get("answer_en", ""),
        "answer_ar": state.get("answer_ar", ""),
        "language": state.get("language", "en"),
        "intent": state.get("intent", "unknown"),
        "retrieved": state.get("retrieved", []),
        "rows": state.get("rows", []),
        "chart": state.get("chart"),
        "citations": state.get("citations", []),
        "confidence": state.get("confidence", "unsupported"),
        "unsupported": state.get("unsupported", True),
        "sql": state.get("validated_sql") or None,
        "sql_params": state.get("validated_params") or {},
        "ai_provider": state.get("answer_provider", "deterministic"),
        "generated_at": datetime.now(timezone.utc),
    }}


NODE_SEQUENCE = [
    detect_language_node,
    classify_intent_node,
    retrieve_indicators_node,
    retrieve_definitions_node,
    retrieve_sources_node,
    determine_query_type_node,
    generate_sql_node,
    validate_sql_node,
    execute_sql_node,
    analyze_result_node,
    generate_chart_node,
    generate_answer_node,
    attach_citations_node,
    safety_check_node,
    final_response_node,
]


def _build_graph():
    if StateGraph is None:
        return None
    graph = StateGraph(AssistantState)
    names = [
        "detect_language", "classify_intent", "retrieve_indicators", "retrieve_definitions",
        "retrieve_sources", "determine_query_type", "generate_sql", "validate_sql", "execute_sql",
        "analyze_result", "generate_chart", "generate_answer", "attach_citations", "safety_check", "final_response",
    ]
    for name, fn in zip(names, NODE_SEQUENCE):
        graph.add_node(name, fn)
    graph.add_edge(START, names[0])
    for left, right in zip(names, names[1:]):
        graph.add_edge(left, right)
    graph.add_edge(names[-1], END)
    return graph.compile()


_compiled_graph = _build_graph()


async def run_assistant_workflow(db: Session, question: str, language: str | None = None) -> dict[str, Any]:
    initial: AssistantState = {"db": db, "question": question, "requested_language": language}
    if _compiled_graph is not None:
        state = await _compiled_graph.ainvoke(initial)
        return state["final"]
    # Dependency-free sequential fallback keeps the workflow operational when LangGraph
    # is not installed in a minimal test environment. Production requirements include it.
    state: AssistantState = dict(initial)
    for node in NODE_SEQUENCE:
        update = await node(state)
        state.update(update)
    return state["final"]
