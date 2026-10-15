from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import User
from app.security.dependencies import get_current_user
from app.services.search_service import global_search

router = APIRouter(prefix="/api", tags=["Search"])


@router.get("/search")
def search(q: str = Query(min_length=2, max_length=200), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return global_search(db, q, user.id)
