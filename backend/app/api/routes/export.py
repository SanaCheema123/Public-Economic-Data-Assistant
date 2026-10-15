from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import User
from app.schemas.export import ExportRequest
from app.security.dependencies import get_current_user
from app.services.export_service import csv_bytes, owned_result, pdf_bytes

router = APIRouter(prefix="/api/export", tags=["Exports"])


@router.post("/csv")
def export_csv(payload: ExportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result, query = owned_result(db, user.id, payload.query_result_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Query result not found")
    data = csv_bytes(result)
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="economic-query-{result.id}.csv"'},
    )


@router.post("/pdf")
def export_pdf(payload: ExportRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result, query = owned_result(db, user.id, payload.query_result_id)
        data = pdf_bytes(db, result, query, payload.language)
    except ValueError:
        raise HTTPException(status_code=404, detail="Query result not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="economic-report-{result.id}.pdf"'},
    )
