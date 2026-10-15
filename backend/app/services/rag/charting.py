from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.schemas.common import ChartSpec


def _year(value: Any) -> str:
    if hasattr(value, "year"):
        return str(value.year)
    text = str(value)
    return text[:4]


def build_chart(rows: list[dict[str, Any]], hint: str, language: str) -> ChartSpec | None:
    if not rows:
        return None
    names = list(dict.fromkeys(str(r.get("indicator_name_ar") if language == "ar" else r.get("indicator_name")) for r in rows))
    title = names[0] if len(names) == 1 else ("مقارنة المؤشرات" if language == "ar" else "Indicator Comparison")
    title_ar = str(rows[0].get("indicator_name_ar") or title)

    regional = [r for r in rows if r.get("region")]
    sectoral = [r for r in rows if r.get("sector")]
    if regional:
        return ChartSpec(type="donut", title=title, title_ar=title_ar,
                         labels=[str(r["region"]) for r in regional], values=[float(r["value"]) for r in regional])
    if sectoral:
        return ChartSpec(type="donut", title=title, title_ar=title_ar,
                         labels=[str(r["sector"]) for r in sectoral], values=[float(r["value"]) for r in sectoral])

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("indicator_name"))].append(row)
    if len(grouped) > 1 or hint == "grouped_bar":
        series = []
        for name, group in grouped.items():
            series.append({"name": name, "x": [_year(r["date"]) for r in group], "y": [float(r["value"]) for r in group]})
        return ChartSpec(type="grouped_bar", title=title, title_ar=title_ar, series=series, x_label="Year", y_label=str(rows[0].get("unit") or "Value"))

    ordered = sorted(rows, key=lambda r: str(r.get("date")))
    chart_type = hint if hint in {"line", "bar", "area"} else "line"
    return ChartSpec(type=chart_type, title=title, title_ar=title_ar,
                     x=[_year(r["date"]) for r in ordered], y=[float(r["value"]) for r in ordered],
                     x_label="Year", y_label=str(rows[0].get("unit") or "Value"))
