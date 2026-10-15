from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import Dataset, Indicator, IndicatorValue, RetrievalDocument, Source


class IngestionError(ValueError):
    pass


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) == 4 and text.isdigit():
        return date(int(text), 1, 1)
    return date.fromisoformat(text[:10])


def ingest_indicator_records(
    db: Session,
    *,
    source_slug: str,
    dataset_slug: str,
    dataset_name_en: str,
    dataset_name_ar: str,
    source_url: str,
    indicator_code: str,
    indicator_name_en: str,
    indicator_name_ar: str,
    description_en: str,
    description_ar: str,
    unit: str,
    frequency: str,
    category: str,
    records: list[dict[str, Any]],
    date_column: str = "date",
    value_column: str = "value",
    region_column: str | None = None,
    sector_column: str | None = None,
    replace_values: bool = False,
    verification_status: str = "verified",
) -> dict[str, Any]:
    source = db.scalar(select(Source).where(Source.slug == source_slug))
    if not source:
        raise IngestionError(f"Source registry entry not found: {source_slug}")
    if source.source_type == "demo" and verification_status == "verified":
        raise IngestionError("Demo sources cannot be marked verified")
    if not source_url.startswith(("https://", "http://")):
        raise IngestionError("A documented source URL is required for ingested datasets")
    if not records:
        raise IngestionError("No source records were supplied")

    dataset = db.scalar(select(Dataset).where(Dataset.slug == dataset_slug))
    if not dataset:
        dataset = Dataset(
            source_id=source.id, slug=dataset_slug, name_en=dataset_name_en, name_ar=dataset_name_ar,
            description_en=f"Imported dataset from {source.name_en}.", description_ar=f"مجموعة بيانات مستوردة من {source.name_ar}.",
            source_url=source_url, update_frequency=frequency, verification_status=verification_status,
            last_updated=date.today(), metadata_json={"ingested": True},
        )
        db.add(dataset); db.flush()
    else:
        if dataset.source_id != source.id:
            raise IngestionError("Existing dataset belongs to a different source")
        dataset.source_url = source_url
        dataset.verification_status = verification_status
        dataset.last_updated = date.today()

    indicator = db.scalar(select(Indicator).where(Indicator.indicator_id == indicator_code))
    if not indicator:
        indicator = Indicator(
            indicator_id=indicator_code, name_en=indicator_name_en, name_ar=indicator_name_ar,
            description_en=description_en, description_ar=description_ar, unit=unit, frequency=frequency,
            source_id=source.id, dataset_id=dataset.id, country="Saudi Arabia", category=category,
            last_updated=date.today(), verification_status=verification_status,
        )
        db.add(indicator); db.flush()
    else:
        indicator.dataset_id = dataset.id; indicator.source_id = source.id; indicator.name_en = indicator_name_en
        indicator.name_ar = indicator_name_ar; indicator.description_en = description_en; indicator.description_ar = description_ar
        indicator.unit = unit; indicator.frequency = frequency; indicator.category = category
        indicator.last_updated = date.today(); indicator.verification_status = verification_status

    if replace_values:
        db.execute(delete(IndicatorValue).where(IndicatorValue.indicator_id == indicator.id))

    inserted = 0
    for row in records:
        if date_column not in row or value_column not in row or row[value_column] in (None, ""):
            continue
        parsed_date = _parse_date(row[date_column])
        region = str(row.get(region_column)).strip() if region_column and row.get(region_column) not in (None, "") else None
        sector = str(row.get(sector_column)).strip() if sector_column and row.get(sector_column) not in (None, "") else None
        value = float(row[value_column])
        existing = db.scalar(select(IndicatorValue).where(
            IndicatorValue.indicator_id == indicator.id,
            IndicatorValue.date == parsed_date,
            IndicatorValue.region == region,
            IndicatorValue.sector == sector,
        ))
        if existing:
            existing.value = value
            existing.dimension_json = {k: v for k, v in row.items() if k not in {date_column, value_column, region_column, sector_column}}
        else:
            db.add(IndicatorValue(
                indicator_id=indicator.id, date=parsed_date, value=value, region=region, sector=sector,
                dimension_json={k: v for k, v in row.items() if k not in {date_column, value_column, region_column, sector_column}},
            ))
        inserted += 1

    doc = db.scalar(select(RetrievalDocument).where(RetrievalDocument.kind == "indicator", RetrievalDocument.ref_id == indicator.id))
    if not doc:
        doc = RetrievalDocument(kind="indicator", ref_id=indicator.id, title_en=indicator.name_en, title_ar=indicator.name_ar,
                                content_en=indicator.description_en, content_ar=indicator.description_ar, keywords=[indicator.name_en, indicator.name_ar], embedding_json=[])
        db.add(doc)
    else:
        doc.title_en=indicator.name_en; doc.title_ar=indicator.name_ar; doc.content_en=indicator.description_en; doc.content_ar=indicator.description_ar
    source.last_synchronization_date = datetime.now(timezone.utc)
    db.commit()
    return {"source_id": source.id, "dataset_id": dataset.id, "indicator_id": indicator.id, "records_processed": inserted, "verification_status": verification_status}
