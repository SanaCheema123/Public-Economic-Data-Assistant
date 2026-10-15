from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ChatMessage, ChatSession, Citation, Query, QueryResult, Source, User
from app.schemas.common import ChatResponse, IndicatorSummary
from app.security.prompt_guard import sanitize_user_text
from app.services.langgraph import run_assistant_workflow


async def process_chat(db: Session, user: User, question: str, language: str | None = None, chat_session_id: str | None = None) -> ChatResponse:
    question = sanitize_user_text(question)
    if chat_session_id:
        chat_session = db.get(ChatSession, chat_session_id)
        if not chat_session or chat_session.user_id != user.id:
            raise ValueError("Chat session was not found")
    else:
        chat_session = ChatSession(user_id=user.id, title=question[:120], language=language or user.preferred_language)
        db.add(chat_session)
        db.flush()
    db.add(ChatMessage(chat_session_id=chat_session.id, role="user", content=question))
    query = Query(user_id=user.id, question=question, language=language or user.preferred_language, status="processing")
    db.add(query)
    db.flush()

    started = time.perf_counter()
    final = await run_assistant_workflow(db, question, language=language or user.preferred_language)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    query.language = final["language"]
    query.intent = final.get("intent")
    query.query_type = "unsupported" if final["unsupported"] else ("sql" if final.get("sql") else "metadata")
    query.generated_sql = final.get("sql")
    query.sql_params = final.get("sql_params") or {}
    query.status = "unsupported" if final["unsupported"] else "complete"
    query.ai_provider = final.get("ai_provider")
    query.latency_ms = elapsed_ms

    retrieved = final.get("retrieved") or []
    first = retrieved[0] if retrieved else None
    result = QueryResult(
        query_id=query.id,
        indicator_id=first.indicator.id if first else None,
        answer_en=final["answer_en"],
        answer_ar=final["answer_ar"],
        data_json=[{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()} for row in final.get("rows", [])],
        chart_json=final["chart"].model_dump() if final.get("chart") else {},
        confidence=final["confidence"],
        unsupported=final["unsupported"],
    )
    db.add(result)
    db.flush()

    citation_outputs = []
    for c in final.get("citations", []):
        # Comparison questions may cite multiple indicators/sources. Persist the
        # exact provenance for each citation instead of assigning every citation
        # to the first retrieved indicator.
        match = next((item for item in retrieved if (
            (not c.indicator_name or item.indicator.name_en == c.indicator_name)
            and (not c.dataset_name or item.dataset.name_en == c.dataset_name)
            and (not c.source_name or item.source.name_en == c.source_name)
        )), None)
        citation = Citation(
            query_result_id=result.id,
            source_id=match.source.id if match else None,
            dataset_id=match.dataset.id if match else None,
            indicator_id=match.indicator.id if match else None,
            title=c.title,
            source_url=c.url,
            period=c.period,
            metadata_json=c.model_dump(),
        )
        db.add(citation)
        db.flush()
        c.id = citation.id
        citation_outputs.append(c)

    assistant_content = final["answer_ar"] if final["language"] == "ar" else final["answer_en"]
    db.add(ChatMessage(chat_session_id=chat_session.id, role="assistant", content=assistant_content, query_result_id=result.id))
    db.commit()

    indicator_summary = None
    if first:
        indicator_summary = IndicatorSummary(
            id=first.indicator.id,
            indicator_id=first.indicator.indicator_id,
            name=first.indicator.name_en,
            name_ar=first.indicator.name_ar,
            unit=first.indicator.unit,
            category=first.indicator.category,
            description=first.indicator.description_en,
            description_ar=first.indicator.description_ar,
            verification_status=first.indicator.verification_status,
        )
    source_payload = []
    for item in retrieved[:3]:
        source_payload.append({
            "id": item.source.id,
            "name_en": item.source.name_en,
            "name_ar": item.source.name_ar,
            "url": item.dataset.source_url or item.source.url,
            "organization_url": item.source.url,
            "dataset": item.dataset.name_en,
            "verification_status": item.dataset.verification_status,
        })
    return ChatResponse(
        query_id=query.id,
        chat_session_id=chat_session.id,
        result_id=result.id,
        answer=final["answer_en"],
        answer_ar=final["answer_ar"],
        language=final["language"],
        indicator=indicator_summary,
        data=result.data_json,
        chart=final.get("chart"),
        citations=citation_outputs,
        sources=source_payload,
        confidence=final["confidence"],
        unsupported=final["unsupported"],
        generated_at=final.get("generated_at") or datetime.now(timezone.utc),
        sql_preview=final.get("sql") if not final["unsupported"] else None,
    )


def get_chat_history(db: Session, user: User, limit: int = 50) -> list[dict]:
    sessions = db.scalars(select(ChatSession).where(ChatSession.user_id == user.id).order_by(ChatSession.updated_at.desc()).limit(limit)).all()
    output = []
    for session in sessions:
        messages = db.scalars(select(ChatMessage).where(ChatMessage.chat_session_id == session.id).order_by(ChatMessage.created_at)).all()
        output.append({
            "id": session.id,
            "title": session.title,
            "language": session.language,
            "updated_at": session.updated_at.isoformat(),
            "messages": [{"id": m.id, "role": m.role, "content": m.content, "query_result_id": m.query_result_id, "created_at": m.created_at.isoformat()} for m in messages],
        })
    return output
