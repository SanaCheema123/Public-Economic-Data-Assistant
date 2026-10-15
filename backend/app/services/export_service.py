from __future__ import annotations

import csv
import html
import io
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Citation, Query, QueryResult


def owned_result(db: Session, user_id: str, result_id: str) -> tuple[QueryResult, Query]:
    row = db.execute(
        select(QueryResult, Query)
        .join(Query, Query.id == QueryResult.query_id)
        .where(QueryResult.id == result_id, Query.user_id == user_id)
    ).first()
    if not row:
        raise ValueError("Query result not found")
    return row[0], row[1]


def csv_bytes(result: QueryResult) -> bytes:
    output = io.StringIO()
    fields = ["date", "indicator", "indicator_ar", "value", "unit", "region", "sector", "source", "dataset", "verification_status"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in result.data_json or []:
        writer.writerow({
            "date": row.get("date"),
            "indicator": row.get("indicator_name"),
            "indicator_ar": row.get("indicator_name_ar"),
            "value": row.get("value"),
            "unit": row.get("unit"),
            "region": row.get("region"),
            "sector": row.get("sector"),
            "source": row.get("source_name"),
            "dataset": row.get("dataset_name"),
            "verification_status": row.get("dataset_verification_status") or row.get("verification_status"),
        })
    return output.getvalue().encode("utf-8-sig")


def _chart_svg(chart: dict[str, Any]) -> str:
    width, height = 760, 260
    pad_l, pad_r, pad_t, pad_b = 50, 25, 25, 45
    x = chart.get("x") or []
    y = chart.get("y") or []
    if chart.get("series"):
        # PDF fallback renders the first series to keep export dependency-light.
        series = chart["series"][0]
        x, y = series.get("x", []), series.get("y", [])
    if not y:
        return ""
    vals = [float(v) for v in y]
    min_y, max_y = min(vals + [0.0]), max(vals + [0.0])
    span = max(max_y - min_y, 1e-9)
    plot_w, plot_h = width - pad_l - pad_r, height - pad_t - pad_b
    points = []
    for i, value in enumerate(vals):
        px = pad_l + (plot_w * i / max(1, len(vals) - 1))
        py = pad_t + plot_h - ((value - min_y) / span * plot_h)
        points.append((px, py))
    path = " ".join(("M" if i == 0 else "L") + f" {px:.1f} {py:.1f}" for i, (px, py) in enumerate(points))
    labels = "".join(f'<text x="{px:.1f}" y="{height-18}" text-anchor="middle" font-size="11" fill="#6b625d">{html.escape(str(x[i])) if i < len(x) else i+1}</text>' for i, (px, _) in enumerate(points))
    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#9f7e6a" />' for px, py in points)
    return f'''<svg viewBox="0 0 {width} {height}" width="100%" xmlns="http://www.w3.org/2000/svg">
    <rect width="100%" height="100%" rx="18" fill="#fbf8f4"/>
    <line x1="{pad_l}" x2="{pad_l}" y1="{pad_t}" y2="{height-pad_b}" stroke="#ded4cc"/>
    <line x1="{pad_l}" x2="{width-pad_r}" y1="{height-pad_b}" y2="{height-pad_b}" stroke="#ded4cc"/>
    <path d="{path}" fill="none" stroke="#9f7e6a" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>{dots}{labels}</svg>'''


def pdf_bytes(db: Session, result: QueryResult, query: Query, language: str = "en") -> bytes:
    citations = db.scalars(select(Citation).where(Citation.query_result_id == result.id)).all()
    is_ar = language == "ar"
    title = "تقرير المساعد الذكي للبيانات الاقتصادية العامة" if is_ar else "Public Economic Data Assistant Report"
    answer = result.answer_ar if is_ar else result.answer_en
    direction = "rtl" if is_ar else "ltr"
    rows = result.data_json or []
    chart_svg = _chart_svg(result.chart_json or {})
    citation_html = "".join(
        f'<li><strong>{html.escape(c.title)}</strong><br><span>{html.escape(c.period or "")}</span><br><span>{html.escape(c.source_url)}</span></li>'
        for c in citations
    ) or "<li>No citation was available.</li>"
    table_rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(row.get(key, '') or ''))}</td>" for key in ["date", "indicator_name", "value", "unit", "region", "source_name", "dataset_name"]) + "</tr>"
        for row in rows[:100]
    )
    generated = datetime.now(timezone.utc).isoformat()
    document = f'''<!doctype html><html dir="{direction}"><head><meta charset="utf-8"><style>
        @page {{ size:A4; margin:18mm; }}
        body {{ font-family: "Noto Sans Arabic", "DejaVu Sans", sans-serif; color:#172030; background:#fff; font-size:11px; direction:{direction}; }}
        h1 {{ font-size:24px; margin:0 0 8px; }} h2 {{ font-size:15px; margin:20px 0 8px; }}
        .meta,.card {{ border:1px solid #e3d5ca; border-radius:14px; padding:12px; background:#fbf8f4; }}
        .notice {{ background:#f5ebe1; border:1px solid #d7bdb0; padding:10px; border-radius:10px; margin:12px 0; font-weight:700; }}
        table {{ width:100%; border-collapse:collapse; font-size:9px; }} th,td {{ padding:6px; border-bottom:1px solid #ece5df; text-align:start; }}
        a {{ color:#795a47; }} li {{ margin-bottom:8px; }}
    </style></head><body>
        <h1>{title}</h1>
        <div class="meta"><strong>{'السؤال' if is_ar else 'Question'}:</strong> {html.escape(query.question)}<br><strong>{'وقت الإنشاء' if is_ar else 'Generated'}:</strong> {generated}</div>
        <h2>{'الإجابة' if is_ar else 'Answer'}</h2><div class="card">{html.escape(answer)}</div>
        <h2>{'الرسم البياني' if is_ar else 'Chart'}</h2>{chart_svg or '<div class="card">No chart for this result.</div>'}
        <h2>{'البيانات' if is_ar else 'Data'}</h2><table><thead><tr>{''.join(f'<th>{x}</th>' for x in ['Date','Indicator','Value','Unit','Region','Source','Dataset'])}</tr></thead><tbody>{table_rows}</tbody></table>
        <h2>{'المصادر والاستشهادات' if is_ar else 'Sources & citations'}</h2><ol>{citation_html}</ol>
    </body></html>'''
    try:
        from weasyprint import HTML
        return HTML(string=document).write_pdf()
    except Exception as exc:
        raise RuntimeError("PDF generation is unavailable in this runtime") from exc
