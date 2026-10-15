from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.entities import Dataset, Indicator, Insight, SavedItem, Source


def global_search(db: Session, query: str, user_id: str | None = None, limit: int = 8) -> dict:
    q = f"%{query.strip()}%"
    indicators = db.scalars(
        select(Indicator).where(
            Indicator.verification_status == "verified",
            or_(Indicator.name_en.ilike(q), Indicator.name_ar.ilike(q), Indicator.description_en.ilike(q), Indicator.description_ar.ilike(q)),
        ).limit(limit)
    ).all()
    datasets = db.scalars(
        select(Dataset).where(
            Dataset.verification_status == "verified",
            or_(Dataset.name_en.ilike(q), Dataset.name_ar.ilike(q)),
        ).limit(limit)
    ).all()
    # Only show sources that actually back at least one synchronized verified
    # dataset. Registry-only sources remain available from /api/sources but are
    # not presented as if live data had been ingested from them.
    sources = db.scalars(
        select(Source).join(Dataset, Dataset.source_id == Source.id).where(
            Dataset.verification_status == "verified",
            or_(Source.name_en.ilike(q), Source.name_ar.ilike(q), Source.organization.ilike(q)),
        ).distinct().limit(limit)
    ).all()
    insights = db.scalars(
        select(Insight).where(
            Insight.verification_status == "verified",
            or_(Insight.title_en.ilike(q), Insight.title_ar.ilike(q), Insight.summary_en.ilike(q), Insight.summary_ar.ilike(q)),
        ).limit(limit)
    ).all()
    saved = []
    if user_id:
        saved = db.scalars(select(SavedItem).where(SavedItem.user_id == user_id, SavedItem.title.ilike(q)).limit(limit)).all()
    return {
        "indicators": [{"id": x.id, "name_en": x.name_en, "name_ar": x.name_ar, "unit": x.unit, "category": x.category} for x in indicators],
        "datasets": [{"id": x.id, "name_en": x.name_en, "name_ar": x.name_ar, "verification_status": x.verification_status} for x in datasets],
        "sources": [{"id": x.id, "name_en": x.name_en, "name_ar": x.name_ar, "url": x.url} for x in sources],
        "insights": [{"id": x.id, "title_en": x.title_en, "title_ar": x.title_ar, "verification_status": x.verification_status} for x in insights],
        "saved": [{"id": x.id, "title": x.title, "item_type": x.item_type} for x in saved],
    }
