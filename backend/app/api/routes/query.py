from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import User
from app.schemas.chat import QueryRequest, QueryValidationRequest
from app.schemas.common import ChatResponse
from app.security.dependencies import get_current_user
from app.services.chat_service import process_chat
from app.services.rag.sql_validator import validate_sql

router = APIRouter(prefix="/api/query", tags=["Query"])


@router.post("", response_model=ChatResponse)
async def query(payload: QueryRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return await process_chat(db, user, payload.question, payload.language)


@router.post("/validate")
def validate(payload: QueryValidationRequest, user: User = Depends(get_current_user)):
    result = validate_sql(payload.sql, payload.params)
    return {"valid": result.valid, "sql": result.sql if result.valid else None, "errors": result.errors}
