from __future__ import annotations

from app.schemas.common import CitationOut


def build_citations(rows: list[dict]) -> list[CitationOut]:
    seen: set[tuple] = set()
    citations: list[CitationOut] = []
    for row in rows:
        key = (row.get("source_id"), row.get("dataset_id"), row.get("indicator_uuid"))
        if key in seen:
            continue
        seen.add(key)
        period_values = sorted({str(r.get("date"))[:4] for r in rows if r.get("indicator_uuid") == row.get("indicator_uuid") and r.get("date")})
        period = period_values[0] if len(period_values) == 1 else (f"{period_values[0]}–{period_values[-1]}" if period_values else None)
        verification = str(row.get("dataset_verification_status") or row.get("verification_status") or "unverified")
        citations.append(CitationOut(
            title=f"{row.get('indicator_name')} — {row.get('dataset_name')}",
            source_name=str(row.get("source_name") or "Unknown source"),
            source_name_ar=str(row.get("source_name_ar") or ""),
            dataset_name=str(row.get("dataset_name") or "Unknown dataset"),
            dataset_name_ar=str(row.get("dataset_name_ar") or ""),
            indicator_name=str(row.get("indicator_name") or ""),
            indicator_name_ar=str(row.get("indicator_name_ar") or ""),
            period=period,
            url=str(row.get("dataset_url") or row.get("source_url") or ""),
            verification_status=verification,
        ))
    return citations
