from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import RetrievalDocument, Source


def _embedding(text: str, dims: int = 384) -> list[float]:
    """Small deterministic embedding used only for local retrieval indexing."""
    vec = [0.0] * dims
    for token in text.lower().replace("/", " ").replace("-", " ").split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dims
        vec[idx] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [round(v / norm, 6) for v in vec]


OFFICIAL_SOURCES = [
    {
        "slug": "gastat", "name_en": "General Authority for Statistics (GASTAT)", "name_ar": "الهيئة العامة للإحصاء",
        "organization": "General Authority for Statistics", "url": "https://www.stats.gov.sa/en",
        "description_en": "Saudi Arabia's official statistical authority.", "description_ar": "الجهة الرسمية للإحصاءات في المملكة العربية السعودية.",
        "update_frequency": "Varies by dataset", "source_type": "official", "reliability_metadata": {"tier": "official", "verified_registry": True},
    },
    {
        "slug": "sama", "name_en": "Saudi Central Bank (SAMA)", "name_ar": "البنك المركزي السعودي",
        "organization": "Saudi Central Bank", "url": "https://www.sama.gov.sa/en-US/Statistics/pages/summary.aspx",
        "description_en": "Official monetary, financial, banking and macroeconomic statistics.", "description_ar": "إحصاءات رسمية نقدية ومالية ومصرفية واقتصادية.",
        "update_frequency": "Daily/Monthly/Quarterly/Annual", "source_type": "official", "reliability_metadata": {"tier": "official", "verified_registry": True},
    },
    {
        "slug": "mep", "name_en": "Ministry of Economy and Planning", "name_ar": "وزارة الاقتصاد والتخطيط",
        "organization": "Ministry of Economy and Planning", "url": "https://www.mep.gov.sa/en",
        "description_en": "Economic planning and development information.", "description_ar": "معلومات الاقتصاد والتخطيط والتنمية.",
        "update_frequency": "Varies", "source_type": "official", "reliability_metadata": {"tier": "official", "verified_registry": True},
    },
    {
        "slug": "data-gov-sa", "name_en": "Saudi Open Data Portal", "name_ar": "البوابة الوطنية للبيانات المفتوحة",
        "organization": "Government of Saudi Arabia", "url": "https://open.data.gov.sa/en",
        "description_en": "National catalogue of Saudi open government datasets.", "description_ar": "الفهرس الوطني للبيانات الحكومية المفتوحة.",
        "update_frequency": "Varies", "source_type": "official", "reliability_metadata": {"tier": "official", "verified_registry": True},
    },
    {
        "slug": "world-bank", "name_en": "World Bank", "name_ar": "البنك الدولي",
        "organization": "World Bank", "url": "https://data.worldbank.org/country/saudi-arabia",
        "description_en": "World Development Indicators and related public time-series for Saudi Arabia.", "description_ar": "مؤشرات التنمية العالمية والسلاسل الزمنية العامة للمملكة العربية السعودية.",
        "update_frequency": "Annual/Varies", "source_type": "international", "reliability_metadata": {"tier": "international", "verified_registry": True, "api": "World Bank Indicators API v2"},
    },
    {
        "slug": "imf", "name_en": "International Monetary Fund (IMF)", "name_ar": "صندوق النقد الدولي",
        "organization": "IMF", "url": "https://www.imf.org/en/Countries/SAU",
        "description_en": "Macroeconomic and fiscal information.", "description_ar": "بيانات الاقتصاد الكلي والمالية العامة.",
        "update_frequency": "Quarterly/Annual", "source_type": "international", "reliability_metadata": {"tier": "international", "verified_registry": True},
    },
    {
        "slug": "oecd", "name_en": "OECD", "name_ar": "منظمة التعاون الاقتصادي والتنمية",
        "organization": "OECD", "url": "https://www.oecd.org/saudi-arabia/",
        "description_en": "Policy and economic indicators.", "description_ar": "مؤشرات اقتصادية وسياسات عامة.",
        "update_frequency": "Varies", "source_type": "international", "reliability_metadata": {"tier": "international", "verified_registry": True},
    },
]


def seed_source_registry(db: Session) -> None:
    """Idempotently seed source metadata only. No statistical values are invented."""
    for item in OFFICIAL_SOURCES:
        source = db.scalar(select(Source).where(Source.slug == item["slug"]))
        if not source:
            source = Source(country="Saudi Arabia", **item)
            db.add(source)
            db.flush()
        else:
            for key, value in item.items():
                setattr(source, key, value)
        doc = db.scalar(select(RetrievalDocument).where(RetrievalDocument.kind == "source", RetrievalDocument.ref_id == source.id))
        text_value = f"{source.name_en} {source.name_ar} {source.description_en} {source.description_ar} {source.organization}"
        if not doc:
            db.add(RetrievalDocument(
                kind="source", ref_id=source.id, title_en=source.name_en, title_ar=source.name_ar,
                content_en=source.description_en, content_ar=source.description_ar,
                keywords=[source.slug, source.organization], embedding_json=_embedding(text_value),
            ))
        else:
            doc.title_en = source.name_en
            doc.title_ar = source.name_ar
            doc.content_en = source.description_en
            doc.content_ar = source.description_ar
            doc.keywords = [source.slug, source.organization]
            doc.embedding_json = _embedding(text_value)
    db.commit()
    sync_pgvector_embeddings(db)


def sync_pgvector_embeddings(db: Session) -> None:
    if not db.bind or db.bind.dialect.name != "postgresql":
        return
    from sqlalchemy import text
    try:
        docs = db.scalars(select(RetrievalDocument)).all()
        for doc in docs:
            if not doc.embedding_json:
                continue
            vec_literal = "[" + ",".join(str(float(v)) for v in doc.embedding_json) + "]"
            db.execute(
                text("UPDATE retrieval_documents SET embedding = CAST(:vec AS vector) WHERE id = :id"),
                {"vec": vec_literal, "id": doc.id},
            )
        db.commit()
    except Exception:
        db.rollback()
