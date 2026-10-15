from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query as Q
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.entities import Dataset, Indicator, IndicatorValue, Source
from app.schemas.common import DatasetOut, SourceOut
from app.security.dependencies import get_current_user
from app.models.entities import User
from app.services.live_data import live_data_status, sync_live_data

router = APIRouter(prefix="/api", tags=["Public data catalog"])


@router.get("/sources", response_model=list[SourceOut])
def sources(db: Session = Depends(get_db)):
    items = db.scalars(select(Source).order_by(Source.source_type, Source.name_en)).all()
    return [SourceOut(
        id=s.id, slug=s.slug, name_en=s.name_en, name_ar=s.name_ar, organization=s.organization, url=s.url,
        description_en=s.description_en, description_ar=s.description_ar, update_frequency=s.update_frequency, country=s.country,
        reliability_metadata=s.reliability_metadata, source_type=s.source_type, last_synchronization_date=s.last_synchronization_date,
        datasets=[{"id": d.id, "name_en": d.name_en, "name_ar": d.name_ar, "verification_status": d.verification_status} for d in s.datasets]
    ) for s in items]


@router.get("/datasets", response_model=list[DatasetOut])
def datasets(source_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Dataset).where(Dataset.verification_status == "verified")
    if source_id:
        stmt = stmt.where(Dataset.source_id == source_id)
    return list(db.scalars(stmt.order_by(Dataset.name_en)).all())


@router.get("/indicators")
def indicators(
    q: str | None = None,
    category: str | None = None,
    limit: int = Q(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    stmt = select(Indicator).where(Indicator.verification_status == "verified")
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Indicator.name_en.ilike(pattern), Indicator.name_ar.ilike(pattern), Indicator.description_en.ilike(pattern), Indicator.description_ar.ilike(pattern)))
    if category and category.lower() != "all":
        stmt = stmt.where(Indicator.category == category)
    items = db.scalars(stmt.order_by(Indicator.category, Indicator.name_en).limit(limit)).all()
    return [{
        "id": i.id, "indicator_id": i.indicator_id, "name_en": i.name_en, "name_ar": i.name_ar,
        "description_en": i.description_en, "description_ar": i.description_ar, "unit": i.unit,
        "frequency": i.frequency, "category": i.category, "country": i.country,
        "last_updated": i.last_updated, "verification_status": i.verification_status,
    } for i in items]


@router.get("/indicators/{indicator_id}")
def indicator_detail(indicator_id: str, db: Session = Depends(get_db)):
    item = db.get(Indicator, indicator_id) or db.scalar(select(Indicator).where(Indicator.indicator_id == indicator_id))
    if not item or item.verification_status != "verified":
        raise HTTPException(status_code=404, detail="Verified indicator not found")
    dataset = db.get(Dataset, item.dataset_id)
    source = db.get(Source, item.source_id)
    values = db.scalars(select(IndicatorValue).where(IndicatorValue.indicator_id == item.id).order_by(IndicatorValue.date, IndicatorValue.region, IndicatorValue.sector)).all()
    return {
        "indicator": {
            "id": item.id, "indicator_id": item.indicator_id, "name_en": item.name_en, "name_ar": item.name_ar,
            "description_en": item.description_en, "description_ar": item.description_ar, "unit": item.unit,
            "frequency": item.frequency, "category": item.category, "verification_status": item.verification_status,
        },
        "dataset": DatasetOut.model_validate(dataset) if dataset else None,
        "source": SourceOut.model_validate(source) if source else None,
        "values": [{"date": v.date, "value": v.value, "region": v.region, "sector": v.sector, "dimension": v.dimension_json} for v in values],
    }


@router.get("/data/status")
def data_status(db: Session = Depends(get_db)):
    return live_data_status(db)


@router.post("/data/sync")
async def data_sync(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await sync_live_data(db, force=True)
