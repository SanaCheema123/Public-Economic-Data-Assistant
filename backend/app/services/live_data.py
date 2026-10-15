from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.seed import sync_pgvector_embeddings
from app.models.entities import Dataset, Indicator, IndicatorValue, RetrievalDocument, Source
from app.services.connectors.http_connectors import GastatConnector, WorldBankConnector
from app.services.connectors.ingestion import ingest_indicator_records

logger = logging.getLogger("peda.live_data")


@dataclass(frozen=True)
class LiveIndicatorSpec:
    code: str
    name_en: str
    name_ar: str
    unit: str
    category: str
    keywords: tuple[str, ...]


WORLD_BANK_INDICATORS: tuple[LiveIndicatorSpec, ...] = (
    LiveIndicatorSpec("NY.GDP.MKTP.KD.ZG", "GDP Growth", "معدل نمو الناتج المحلي الإجمالي", "%", "Economy", ("gdp", "growth", "real gdp", "economic growth", "الناتج", "المحلي", "الإجمالي", "النمو")),
    LiveIndicatorSpec("NY.GDP.MKTP.CN", "GDP (current SAR)", "الناتج المحلي الإجمالي بالأسعار الجارية", "SAR", "Economy", ("gdp", "current sar", "current lcu", "economy", "الناتج المحلي", "ريال")),
    LiveIndicatorSpec("NY.GDP.PCAP.CD", "GDP per Capita", "نصيب الفرد من الناتج المحلي الإجمالي", "US$", "Economy", ("gdp per capita", "income per person", "نصيب الفرد", "الناتج")),
    LiveIndicatorSpec("FP.CPI.TOTL.ZG", "Inflation Rate", "معدل التضخم", "%", "Prices", ("inflation", "consumer prices", "cpi", "التضخم", "الأسعار", "المستهلك")),
    LiveIndicatorSpec("SL.UEM.TOTL.ZS", "Unemployment Rate", "معدل البطالة", "%", "Labor Market", ("unemployment", "jobless", "labor market", "البطالة", "سوق العمل")),
    LiveIndicatorSpec("SP.POP.TOTL", "Population", "عدد السكان", "people", "Population", ("population", "people", "residents", "السكان", "عدد السكان")),
    LiveIndicatorSpec("SP.POP.GROW", "Population Growth", "معدل نمو السكان", "%", "Population", ("population growth", "demographic growth", "نمو السكان", "السكان")),
    LiveIndicatorSpec("SL.TLF.TOTL.IN", "Labor Force", "إجمالي القوى العاملة", "people", "Labor Market", ("labor force", "workforce", "employment", "القوى العاملة", "العمل")),
    LiveIndicatorSpec("SL.TLF.CACT.ZS", "Labor Force Participation Rate", "معدل المشاركة في القوى العاملة", "%", "Labor Market", ("labor force participation", "participation rate", "workforce participation", "المشاركة", "القوى العاملة")),
    LiveIndicatorSpec("SL.TLF.CACT.FE.ZS", "Female Labor Force Participation Rate", "معدل مشاركة الإناث في القوى العاملة", "%", "Labor Market", ("female labor", "women workforce", "female participation", "مشاركة الإناث", "المرأة", "القوى العاملة")),
    LiveIndicatorSpec("BX.KLT.DINV.WD.GD.ZS", "Foreign Direct Investment, Net Inflows", "صافي تدفقات الاستثمار الأجنبي المباشر", "% of GDP", "Economy", ("fdi", "foreign direct investment", "investment inflows", "الاستثمار الأجنبي", "الاستثمار المباشر")),
    LiveIndicatorSpec("NY.GDP.PETR.RT.ZS", "Oil Rents", "ريع النفط", "% of GDP", "Economy", ("oil rents", "petroleum", "oil contribution", "النفط", "ريع النفط")),
)

GASTAT_HEADLINE_CODES = {
    "GASTAT.POPULATION_ESTIMATE",
    "GASTAT.REAL_GDP_GROWTH",
    "GASTAT.SAUDI_UNEMPLOYMENT",
    "GASTAT.CPI_INFLATION",
    "GASTAT.INDUSTRIAL_PRODUCTION",
}

GASTAT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "GASTAT.POPULATION_ESTIMATE": ("population", "population estimate", "people", "السكان", "تقدير السكان"),
    "GASTAT.REAL_GDP_GROWTH": ("gdp", "real gdp", "gdp growth", "quarterly gdp", "الناتج المحلي", "النمو الحقيقي"),
    "GASTAT.SAUDI_UNEMPLOYMENT": ("unemployment", "saudi unemployment", "citizen unemployment", "labor market", "البطالة", "السعوديين", "سوق العمل"),
    "GASTAT.CPI_INFLATION": ("inflation", "cpi", "consumer prices", "التضخم", "الأسعار"),
    "GASTAT.INDUSTRIAL_PRODUCTION": ("industrial production", "production index", "industry", "الإنتاج الصناعي", "الصناعة"),
}


def _embedding(text_value: str, dims: int = 384) -> list[float]:
    vec = [0.0] * dims
    for token in text_value.lower().replace("/", " ").replace("-", " ").split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dims
        vec[idx] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


def _human_url(code: str) -> str:
    return f"https://data.worldbank.org/indicator/{code}?locations=SA"


def _dataset_slug(code: str) -> str:
    return "world-bank-sau-" + code.lower().replace(".", "-")


def _source_needs_refresh(db: Session, slug: str, max_age: timedelta) -> bool:
    source = db.scalar(select(Source).where(Source.slug == slug))
    if not source or not source.last_synchronization_date:
        return True
    stamp = source.last_synchronization_date
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - stamp >= max_age


def _world_bank_needs_refresh(db: Session) -> bool:
    if settings.data_mode != "live":
        return False
    required_codes = {spec.code for spec in WORLD_BANK_INDICATORS}
    available_codes = set(db.scalars(select(Indicator.indicator_id).where(
        Indicator.verification_status == "verified",
        Indicator.indicator_id.in_(required_codes),
    )).all())
    if available_codes != required_codes:
        return True
    return _source_needs_refresh(db, "world-bank", timedelta(hours=max(settings.data_refresh_hours, 1)))


def _gastat_needs_refresh(db: Session) -> bool:
    if settings.data_mode != "live" or not settings.gastat_headlines_enabled:
        return False
    available = set(db.scalars(select(Indicator.indicator_id).where(
        Indicator.verification_status == "verified",
        Indicator.indicator_id.in_(GASTAT_HEADLINE_CODES),
    )).all())
    # Three core official headline indicators are enough to consider the page parsed;
    # missing headline items are retried on the next refresh.
    if len(available & {"GASTAT.REAL_GDP_GROWTH", "GASTAT.SAUDI_UNEMPLOYMENT", "GASTAT.CPI_INFLATION"}) < 3:
        return True
    return _source_needs_refresh(db, "gastat", timedelta(minutes=max(settings.gastat_refresh_minutes, 5)))




def _record_sync_attempt(db: Session, slug: str, error: str | None) -> None:
    source = db.scalar(select(Source).where(Source.slug == slug))
    if not source:
        return
    metadata = dict(source.reliability_metadata or {})
    metadata["last_sync_attempt"] = datetime.now(timezone.utc).isoformat()
    if error:
        metadata["last_sync_error"] = error
    else:
        metadata.pop("last_sync_error", None)
    source.reliability_metadata = metadata
    db.commit()

def _purge_demo_data(db: Session) -> None:
    demo_indicators = db.scalars(select(Indicator).where(Indicator.verification_status == "demo")).all()
    for indicator in demo_indicators:
        db.execute(delete(RetrievalDocument).where(RetrievalDocument.kind == "indicator", RetrievalDocument.ref_id == indicator.id))
        db.delete(indicator)
    for dataset in db.scalars(select(Dataset).where(Dataset.verification_status == "demo")).all():
        db.delete(dataset)
    for source in db.scalars(select(Source).where(Source.source_type == "demo")).all():
        db.delete(source)
    db.commit()


def live_data_status(db: Session) -> dict[str, Any]:
    verified_indicators = db.scalar(select(func.count(Indicator.id)).where(Indicator.verification_status == "verified")) or 0
    verified_values = db.scalar(
        select(func.count(IndicatorValue.id)).join(Indicator, Indicator.id == IndicatorValue.indicator_id).where(Indicator.verification_status == "verified")
    ) or 0
    wb = db.scalar(select(Source).where(Source.slug == "world-bank"))
    gastat = db.scalar(select(Source).where(Source.slug == "gastat"))
    latest_value_date = db.scalar(
        select(func.max(IndicatorValue.date)).join(Indicator, Indicator.id == IndicatorValue.indicator_id).where(Indicator.verification_status == "verified")
    )
    wb_codes = {spec.code for spec in WORLD_BANK_INDICATORS}
    wb_available = set(db.scalars(select(Indicator.indicator_id).where(
        Indicator.verification_status == "verified", Indicator.indicator_id.in_(wb_codes)
    )).all())
    gastat_available = set(db.scalars(select(Indicator.indicator_id).where(
        Indicator.verification_status == "verified", Indicator.indicator_id.in_(GASTAT_HEADLINE_CODES)
    )).all())
    core_wb = {"NY.GDP.MKTP.KD.ZG", "SL.UEM.TOTL.ZS", "FP.CPI.TOTL.ZG", "SP.POP.GROW"}
    core_gastat = {"GASTAT.REAL_GDP_GROWTH", "GASTAT.SAUDI_UNEMPLOYMENT", "GASTAT.CPI_INFLATION"}
    wb_ready = core_wb <= wb_available
    gastat_ready = core_gastat <= gastat_available
    def stamp(source: Source | None) -> str | None:
        return source.last_synchronization_date.isoformat() if source and source.last_synchronization_date else None
    stamps = [x for x in [wb.last_synchronization_date if wb else None, gastat.last_synchronization_date if gastat else None] if x]
    newest_sync = max(stamps).isoformat() if stamps else None
    return {
        "mode": "live",
        "provider": "GASTAT official headlines + World Bank Indicators API v2",
        "verified_indicators": int(verified_indicators),
        "verified_values": int(verified_values),
        "core_indicators_ready": len(core_wb & wb_available),
        "expected_core_indicators": len(core_wb),
        "official_headlines_ready": gastat_ready,
        "gastat_headlines": len(gastat_available),
        "world_bank_indicators": len(wb_available),
        "latest_observation_date": latest_value_date.isoformat() if latest_value_date else None,
        "last_synchronization_date": newest_sync,
        "sources": {
            "gastat": {"ready": gastat_ready, "last_sync": stamp(gastat), "official": True, "last_error": (gastat.reliability_metadata or {}).get("last_sync_error") if gastat else None},
            "world_bank": {"ready": wb_ready, "last_sync": stamp(wb), "official": False, "last_error": (wb.reliability_metadata or {}).get("last_sync_error") if wb else None},
        },
        "refresh_hours": settings.data_refresh_hours,
        "gastat_refresh_minutes": settings.gastat_refresh_minutes,
        "ready": (gastat_ready or wb_ready) and bool(verified_values),
    }


async def sync_gastat_headlines(db: Session, force: bool = False) -> dict[str, Any]:
    if settings.data_mode != "live":
        return {"ok": False, "skipped": True, "reason": "DATA_MODE is not live"}
    if not settings.gastat_headlines_enabled:
        return {"ok": False, "skipped": True, "reason": "GASTAT_HEADLINES_ENABLED is false"}
    if not force and not _gastat_needs_refresh(db):
        return {"ok": True, "skipped": True, "reason": "GASTAT headlines are still fresh"}

    result = await GastatConnector().fetch_headlines()
    if not result.ok:
        error = result.error or "GASTAT fetch failed"
        _record_sync_attempt(db, "gastat", error)
        return {"ok": False, "source": "gastat", "error": error, "synced_indicators": 0}

    successes = 0
    failures: list[dict[str, str]] = []
    for row in result.records:
        try:
            code = str(row["indicator"])
            period = str(row.get("period") or row.get("date") or "latest")
            name_en = str(row["name_en"])
            name_ar = str(row["name_ar"])
            description_en = f"Official GASTAT Main Indicator. Published period: {period}. Fetched directly from stats.gov.sa."
            description_ar = f"مؤشر رئيسي رسمي من الهيئة العامة للإحصاء. فترة النشر: {period}. تم جلبه مباشرة من stats.gov.sa."
            payload = ingest_indicator_records(
                db,
                source_slug="gastat",
                dataset_slug="gastat-main-indicators-" + code.lower().replace(".", "-"),
                dataset_name_en=f"GASTAT Main Indicators — {name_en}",
                dataset_name_ar=f"المؤشرات الرئيسية للهيئة العامة للإحصاء — {name_ar}",
                source_url=str(row.get("source_url") or "https://stats.gov.sa/en/"),
                indicator_code=code,
                indicator_name_en=name_en,
                indicator_name_ar=name_ar,
                description_en=description_en,
                description_ar=description_ar,
                unit=str(row["unit"]),
                frequency=str(row["frequency"]),
                category=str(row["category"]),
                records=[{
                    "date": row["date"],
                    "value": row["value"],
                    "period": period,
                    "live": True,
                    "official": True,
                    "provider": "GASTAT",
                }],
                replace_values=False,
                verification_status="verified",
            )
            indicator = db.get(Indicator, payload["indicator_id"])
            dataset = db.get(Dataset, payload["dataset_id"])
            if indicator and dataset:
                dataset.metadata_json = {
                    "live": True,
                    "official": True,
                    "provider": "General Authority for Statistics (GASTAT)",
                    "page": result.metadata.get("url") or "https://stats.gov.sa/en/",
                    "period": period,
                }
                doc = db.scalar(select(RetrievalDocument).where(RetrievalDocument.kind == "indicator", RetrievalDocument.ref_id == indicator.id))
                keywords = GASTAT_KEYWORDS.get(code, (name_en, name_ar))
                if doc:
                    doc.keywords = list(keywords)
                    doc.embedding_json = _embedding(" ".join([name_en, name_ar, description_en, description_ar, *keywords]))
            db.commit()
            successes += 1
        except Exception as exc:
            db.rollback()
            failures.append({"indicator": str(row.get("indicator") or "unknown"), "error": type(exc).__name__})

    _purge_demo_data(db)
    _record_sync_attempt(db, "gastat", None if successes else "No GASTAT headline indicators were synchronized")
    sync_pgvector_embeddings(db)
    return {"ok": successes > 0, "source": "gastat", "synced_indicators": successes, "failures": failures}


async def sync_world_bank_live_data(db: Session, force: bool = False) -> dict[str, Any]:
    if settings.data_mode != "live":
        return {"ok": False, "skipped": True, "reason": "DATA_MODE is not live"}
    if not force and not _world_bank_needs_refresh(db):
        return {"ok": True, "skipped": True, "reason": "World Bank live data is still fresh", **live_data_status(db)}

    connector = WorldBankConnector()
    end_year = datetime.now(timezone.utc).year + 1

    async def fetch_one(spec: LiveIndicatorSpec):
        values_task = connector.fetch(spec.code, start_year=settings.live_data_start_year, end_year=end_year, country=settings.live_data_country)
        metadata_task = connector.fetch_metadata(spec.code)
        return spec, *(await asyncio.gather(values_task, metadata_task))

    fetched = await asyncio.gather(*(fetch_one(spec) for spec in WORLD_BANK_INDICATORS))
    successes = 0
    failures: list[dict[str, str]] = []
    for spec, result, meta_result in fetched:
        if not result.ok or not result.records:
            failures.append({"indicator": spec.code, "error": result.error or "No live observations returned"})
            continue
        metadata_row = meta_result.records[0] if meta_result.ok and meta_result.records else {}
        description_en = str(metadata_row.get("sourceNote") or f"Live World Bank indicator {spec.code} for Saudi Arabia.")
        source_org = str(metadata_row.get("sourceOrganization") or "World Bank Indicators API")
        description_ar = f"سلسلة زمنية منشورة للمملكة العربية السعودية للمؤشر {spec.name_ar}، متزامنة من واجهة مؤشرات البنك الدولي."
        payload = ingest_indicator_records(
            db,
            source_slug="world-bank",
            dataset_slug=_dataset_slug(spec.code),
            dataset_name_en=f"World Development Indicators — {spec.name_en}",
            dataset_name_ar=f"مؤشرات التنمية العالمية — {spec.name_ar}",
            source_url=_human_url(spec.code),
            indicator_code=spec.code,
            indicator_name_en=spec.name_en,
            indicator_name_ar=spec.name_ar,
            description_en=description_en,
            description_ar=description_ar,
            unit=spec.unit,
            frequency="Annual",
            category=spec.category,
            records=result.records,
            replace_values=True,
            verification_status="verified",
        )
        indicator = db.get(Indicator, payload["indicator_id"])
        dataset = db.get(Dataset, payload["dataset_id"])
        if indicator and dataset:
            dataset.metadata_json = {
                "live": True,
                "provider": "World Bank Indicators API v2",
                "indicator_code": spec.code,
                "api_url": result.metadata.get("url"),
                "api_lastupdated": result.metadata.get("lastupdated"),
                "source_organization": source_org,
                "license": "See World Bank indicator page",
            }
            doc = db.scalar(select(RetrievalDocument).where(RetrievalDocument.kind == "indicator", RetrievalDocument.ref_id == indicator.id))
            text_value = " ".join([spec.name_en, spec.name_ar, description_en, description_ar, *spec.keywords])
            if doc:
                doc.keywords = list(spec.keywords)
                doc.embedding_json = _embedding(text_value)
        successes += 1

    _purge_demo_data(db)
    _record_sync_attempt(db, "world-bank", None if successes else (failures[0]["error"] if failures else "No World Bank indicators were synchronized"))
    sync_pgvector_embeddings(db)
    status = live_data_status(db)
    logger.info("world_bank_sync_complete indicators=%s failures=%s latest=%s", successes, len(failures), status.get("latest_observation_date"))
    return {"ok": successes > 0, "source": "world-bank", "synced_indicators": successes, "failures": failures, **status}


async def sync_live_data(db: Session, force: bool = False) -> dict[str, Any]:
    """Synchronize real upstream sources. No sample statistics are generated here."""
    if settings.data_mode != "live":
        return {"ok": False, "skipped": True, "reason": "DATA_MODE is not live"}

    gastat_result: dict[str, Any]
    wb_result: dict[str, Any]
    try:
        gastat_result = await sync_gastat_headlines(db, force=force)
    except Exception as exc:
        db.rollback()
        gastat_result = {"ok": False, "source": "gastat", "error": f"{type(exc).__name__}: synchronization failed"}
    try:
        wb_result = await sync_world_bank_live_data(db, force=force)
    except Exception as exc:
        db.rollback()
        wb_result = {"ok": False, "source": "world-bank", "error": f"{type(exc).__name__}: synchronization failed"}

    _purge_demo_data(db)
    status = live_data_status(db)
    ok = bool(gastat_result.get("ok") or gastat_result.get("skipped") or wb_result.get("ok") or wb_result.get("skipped")) and status["ready"]
    logger.info(
        "live_sync_complete ok=%s gastat=%s world_bank=%s official_ready=%s",
        ok,
        gastat_result.get("ok"),
        wb_result.get("ok"),
        status.get("official_headlines_ready"),
    )
    return {"ok": ok, "gastat": gastat_result, "world_bank": wb_result, **status}
