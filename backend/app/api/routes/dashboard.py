from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import User
from app.security.dependencies import get_current_user
from app.services.dashboard_service import dashboard_payload, insights_payload

router = APIRouter(prefix="/api", tags=["Dashboard"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return dashboard_payload(db, user.id)


@router.get("/insights")
def insights(
    category: str | None = None,
    years: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return insights_payload(db, category, years)
