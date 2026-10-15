from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Dataset, Indicator, IndicatorValue, Query, Source
from app.services.live_data import live_data_status

# Dashboard headline cards prefer GASTAT's official Saudi headline values. If
# the GASTAT page is temporarily unavailable, the application falls back to
# the corresponding verified World Bank series rather than inventing a number.
KPI_CANDIDATES = [
    ("GASTAT.REAL_GDP_GROWTH", "NY.GDP.MKTP.KD.ZG"),
    ("GASTAT.SAUDI_UNEMPLOYMENT", "SL.UEM.TOTL.ZS"),
    ("GASTAT.CPI_INFLATION", "FP.CPI.TOTL.ZG"),
    ("SP.POP.GROW",),
]

# Historical trend charts use the World Bank API because it exposes a stable,
# machine-readable time series with consistent annual semantics.
TREND_CODES = ["NY.GDP.MKTP.KD.ZG", "SL.UEM.TOTL.ZS", "FP.CPI.TOTL.ZG"]


def _series(db: Session, indicator_code: str, years: int = 5) -> dict | None:
    indicator = db.scalar(select(Indicator).where(
        Indicator.indicator_id == indicator_code,
        Indicator.verification_status == "verified",
    ))
    if not indicator:
        return None
    values = db.scalars(
        select(IndicatorValue)
        .where(IndicatorValue.indicator_id == indicator.id)
        .order_by(IndicatorValue.date.desc())
        .limit(years)
    ).all()
    values = list(reversed(values))
    if not values:
        return None
    latest = values[-1]
    previous = values[-2] if len(values) > 1 else None
    source = db.get(Source, indicator.source_id)
    dataset = db.get(Dataset, indicator.dataset_id)
    delta = round(latest.value - previous.value, 3) if previous else None
    period = (latest.dimension_json or {}).get("period") or latest.date.isoformat()
    return {
        "id": indicator.id,
        "indicator_id": indicator.indicator_id,
        "name_en": indicator.name_en,
        "name_ar": indicator.name_ar,
        "unit": indicator.unit,
        "category": indicator.category,
        "verification_status": indicator.verification_status,
        "value": latest.value,
        "date": latest.date.isoformat(),
        "period_label": period,
        "delta": delta,
        "series": [{"date": v.date.isoformat(), "value": v.value} for v in values],
        "source": {
            "id": source.id if source else None,
            "slug": source.slug if source else None,
            "name_en": source.name_en if source else None,
            "name_ar": source.name_ar if source else None,
            "url": dataset.source_url if dataset else (source.url if source else None),
            "official": bool(source and source.source_type == "official"),
            "last_sync": source.last_synchronization_date.isoformat() if source and source.last_synchronization_date else None,
        },
    }


def _preferred_series(db: Session, candidates: tuple[str, ...], years: int = 5) -> dict | None:
    for code in candidates:
        item = _series(db, code, years=years)
        if item:
            return item
    return None


def dashboard_payload(db: Session, user_id: str | None = None) -> dict:
    kpis = [item for candidates in KPI_CANDIDATES if (item := _preferred_series(db, candidates))]
    trends = [item for code in TREND_CODES if (item := _series(db, code))]
    recent = []
    if user_id:
        queries = db.scalars(select(Query).where(Query.user_id == user_id).order_by(Query.created_at.desc()).limit(4)).all()
        recent = [{"id": q.id, "question": q.question, "language": q.language, "created_at": q.created_at.isoformat()} for q in queries]

    used_source_ids = db.scalars(
        select(Indicator.source_id).where(Indicator.verification_status == "verified").distinct()
    ).all()
    sources = db.scalars(select(Source).where(Source.id.in_(used_source_ids)).order_by(Source.source_type, Source.name_en)).all() if used_source_ids else []
    status = live_data_status(db)
    latest_labels = [item.get("period_label") for item in kpis if item.get("period_label")]
    official_count = sum(1 for item in kpis if item.get("source", {}).get("official"))
    if kpis:
        summary_en = (
            f"Headline cards are loaded from synchronized public sources; {official_count} currently come directly from GASTAT. "
            "Historical trend charts use the World Bank Indicators API. Each card shows its exact source and published period."
        )
        summary_ar = (
            f"يتم تحميل المؤشرات الرئيسية من مصادر عامة متزامنة؛ ويأتي {official_count} منها حالياً مباشرة من الهيئة العامة للإحصاء. "
            "تستخدم الرسوم التاريخية واجهة مؤشرات البنك الدولي، ويعرض كل مؤشر مصدره وفترة نشره بدقة."
        )
    else:
        summary_en = "No live public observations are available. The application will not substitute demo statistics."
        summary_ar = "لا تتوفر حالياً مشاهدات عامة حية، ولن يستبدل التطبيق ذلك ببيانات تجريبية."
    return {
        "kpis": kpis,
        "trends": trends,
        "recent_questions": recent,
        "summary": {"en": summary_en, "ar": summary_ar, "live": True, "periods": latest_labels},
        "sources": [{"id": s.id, "name_en": s.name_en, "name_ar": s.name_ar, "url": s.url, "slug": s.slug, "source_type": s.source_type} for s in sources],
        "data_status": status,
    }


def insights_payload(db: Session, category: str | None = None, years: int = 5) -> dict:
    stmt = select(Indicator).where(Indicator.verification_status == "verified")
    if category and category.lower() != "all":
        stmt = stmt.where(Indicator.category == category)
    indicators = db.scalars(stmt.order_by(Indicator.category, Indicator.name_en)).all()
    cards = []
    series = []
    for indicator in indicators:
        values = db.scalars(
            select(IndicatorValue)
            .where(IndicatorValue.indicator_id == indicator.id)
            .order_by(IndicatorValue.date.desc())
            .limit(years)
        ).all()
        values = list(reversed(values))
        if not values:
            continue
        latest = values[-1]
        source = db.get(Source, indicator.source_id)
        dataset = db.get(Dataset, indicator.dataset_id)
        cards.append({
            "id": indicator.id,
            "indicator_id": indicator.indicator_id,
            "name_en": indicator.name_en,
            "name_ar": indicator.name_ar,
            "unit": indicator.unit,
            "value": latest.value,
            "date": latest.date.isoformat(),
            "period_label": (latest.dimension_json or {}).get("period") or latest.date.isoformat(),
            "category": indicator.category,
            "verification_status": indicator.verification_status,
            "source": {
                "name_en": source.name_en if source else None,
                "name_ar": source.name_ar if source else None,
                "url": dataset.source_url if dataset else (source.url if source else None),
                "official": bool(source and source.source_type == "official"),
            },
        })
        series.append({
            "id": indicator.id,
            "indicator_id": indicator.indicator_id,
            "name_en": indicator.name_en,
            "name_ar": indicator.name_ar,
            "unit": indicator.unit,
            "values": [{"date": v.date.isoformat(), "value": v.value, "region": v.region, "sector": v.sector} for v in values],
        })
    status = live_data_status(db)
    return {
        "cards": cards,
        "series": series,
        "live": True,
        "data_status": status,
        "summary": {
            "en": "This page uses only synchronized verified upstream observations. Official GASTAT headline values are preferred for the latest Saudi indicators; World Bank series provide historical context.",
            "ar": "تستخدم هذه الصفحة فقط مشاهدات موثوقة ومتزامنة من المصادر الأصلية. تُفضّل مؤشرات الهيئة العامة للإحصاء لأحدث القيم السعودية، وتوفر سلاسل البنك الدولي السياق التاريخي.",
        },
    }
