from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import User
from app.schemas.chat import ChatRequest
from app.schemas.feedback import FeedbackRequest
from app.schemas.common import ChatResponse
from app.security.dependencies import get_current_user
from app.services.chat_service import get_chat_history, process_chat
from app.models.entities import QueryResult, Query, AuditLog
from sqlalchemy import select

router = APIRouter(prefix="/api", tags=["AI assistant"])


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        return await process_chat(db, user, payload.question, payload.language, payload.chat_session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/chat/history")
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_chat_history(db, user)


@router.post("/feedback")
def feedback(payload: FeedbackRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned = db.scalar(select(QueryResult.id).join(Query, Query.id == QueryResult.query_id).where(QueryResult.id == payload.query_result_id, Query.user_id == user.id))
    if not owned:
        raise HTTPException(status_code=404, detail="Query result not found")
    db.add(AuditLog(user_id=user.id, action="chat.feedback", metadata_json={"query_result_id": payload.query_result_id, "rating": payload.rating}))
    db.commit()
    return {"message": "Feedback recorded"}
