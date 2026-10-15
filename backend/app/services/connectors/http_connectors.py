from __future__ import annotations

import calendar
import csv
import io
import re
from datetime import date
from html.parser import HTMLParser
from typing import Any

import httpx

from app.core.config import settings
from app.services.connectors.base import BaseDataConnector, ConnectorResult


class _VisibleTextCollector(HTMLParser):
    """Small stdlib HTML text extractor used for the public GASTAT page.

    Keeping this parser in the standard library means the backend can still
    boot even when optional HTML parsing packages have not been installed yet.
    Script/style/noscript blocks are intentionally ignored.
    """

    _ignored_tags = {"script", "style", "noscript", "template"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # type: ignore[override]
        if tag.lower() in self._ignored_tags:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._ignored_tags and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth == 0 and data.strip():
            self.parts.append(data)


def _html_text_lines(html: str) -> list[str]:
    parser = _VisibleTextCollector()
    parser.feed(html)
    parser.close()
    return [
        compact
        for raw in parser.parts
        if (compact := re.sub(r"\s+", " ", raw).strip())
    ]


class URLDataConnector(BaseDataConnector):
    """Connector for explicitly configured official CSV/JSON endpoints."""
    source_slug = "generic"

    async def fetch(self, url: str, format: str = "json", **kwargs) -> ConnectorResult:
        if not url.startswith(("https://", "http://")):
            return ConnectorResult(False, self.source_slug, error="A documented http(s) source URL is required")
        try:
            async with httpx.AsyncClient(timeout=settings.data_sync_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
            if format.lower() == "csv":
                reader = csv.DictReader(io.StringIO(response.text))
                records = [dict(row) for row in reader]
            else:
                payload = response.json()
                if isinstance(payload, list):
                    records = payload
                elif isinstance(payload, dict):
                    records = payload.get("data") if isinstance(payload.get("data"), list) else [payload]
                else:
                    records = []
            return ConnectorResult(True, self.source_slug, records=records, metadata={"url": url, "count": len(records)})
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: source fetch failed")


class GastatConnector(URLDataConnector):
    source_slug = "gastat"
    homepage = "https://stats.gov.sa/en/"

    @staticmethod
    def _previous_numeric(lines: list[str], index: int) -> str | None:
        numeric = re.compile(r"^[+\-]?\s*\d[\d,]*(?:\.\d+)?\s*%?$")
        for candidate in reversed(lines[max(0, index - 8):index]):
            compact = re.sub(r"\s+", " ", candidate).strip()
            if numeric.fullmatch(compact):
                return compact
        return None

    @staticmethod
    def _number(text: str) -> float:
        return float(text.replace(",", "").replace("%", "").replace(" ", ""))

    @staticmethod
    def _period_date(label: str) -> date:
        year_match = re.search(r"\b(20\d{2}|19\d{2})\b", label)
        year = int(year_match.group(1)) if year_match else date.today().year
        lower = label.lower()
        quarter_months = {
            "first quarter": 3,
            "second quarter": 6,
            "third quarter": 9,
            "fourth quarter": 12,
            "q1": 3,
            "q2": 6,
            "q3": 9,
            "q4": 12,
        }
        for token, month in quarter_months.items():
            if token in lower:
                return date(year, month, calendar.monthrange(year, month)[1])
        for month in range(1, 13):
            if calendar.month_name[month].lower() in lower:
                return date(year, month, calendar.monthrange(year, month)[1])
        return date(year, 12, 31)

    async def fetch_headlines(self, **kwargs) -> ConnectorResult:
        """Fetch GASTAT's public Main Indicators directly from the official homepage.

        This endpoint is public and keyless. It is used only for headline values
        that GASTAT itself publishes on the page; no value is estimated or
        backfilled by the application.
        """
        try:
            async with httpx.AsyncClient(timeout=settings.data_sync_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    self.homepage,
                    headers={
                        "Accept": "text/html,application/xhtml+xml",
                        "User-Agent": "PublicEconomicDataAssistant/1.0 (+https://stats.gov.sa/)",
                    },
                )
                response.raise_for_status()
            lines = _html_text_lines(response.text)
            records: list[dict[str, Any]] = []
            specs = [
                ("GASTAT.POPULATION_ESTIMATE", ("population estimates publication",), "Population Estimate", "تقدير عدد السكان", "people", "Population", "Annual"),
                ("GASTAT.REAL_GDP_GROWTH", ("real gdp growth rate",), "Real GDP Growth", "معدل نمو الناتج المحلي الإجمالي الحقيقي", "%", "Economy", "Quarterly"),
                ("GASTAT.SAUDI_UNEMPLOYMENT", ("saudi unemployment",), "Saudi Unemployment Rate", "معدل البطالة بين السعوديين", "%", "Labor Market", "Quarterly"),
                ("GASTAT.CPI_INFLATION", ("inflation",), "Inflation Rate", "معدل التضخم", "%", "Prices", "Monthly"),
                ("GASTAT.INDUSTRIAL_PRODUCTION", ("industrial production index",), "Industrial Production Index Growth", "نمو مؤشر الإنتاج الصناعي", "%", "Economy", "Monthly"),
            ]
            for code, needles, name_en, name_ar, unit, category, frequency in specs:
                for idx, line in enumerate(lines):
                    lowered = line.lower()
                    if not any(needle in lowered for needle in needles):
                        continue
                    raw_value = self._previous_numeric(lines, idx)
                    if raw_value is None:
                        same_line = re.match(r"^([+\-]?\s*\d[\d,]*(?:\.\d+)?\s*%?)\b", line)
                        raw_value = same_line.group(1) if same_line else None
                    if raw_value is None:
                        continue
                    value = self._number(raw_value)
                    period_label = line
                    records.append({
                        "indicator": code,
                        "name_en": name_en,
                        "name_ar": name_ar,
                        "unit": unit,
                        "category": category,
                        "frequency": frequency,
                        "date": self._period_date(period_label).isoformat(),
                        "value": value,
                        "period": period_label,
                        "source_url": self.homepage,
                    })
                    break
            if not records:
                return ConnectorResult(False, self.source_slug, error="GASTAT homepage loaded but no Main Indicators could be parsed")
            return ConnectorResult(
                True,
                self.source_slug,
                records=records,
                metadata={"url": str(response.url), "count": len(records), "live": True, "official": True},
            )
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: GASTAT headline fetch failed")


class OpenDataConnector(URLDataConnector):
    source_slug = "data-gov-sa"


class MinistryEconomyConnector(URLDataConnector):
    source_slug = "mep"


class IMFConnector(URLDataConnector):
    source_slug = "imf"


class OECDConnector(URLDataConnector):
    source_slug = "oecd"


class SamaConnector(BaseDataConnector):
    """SAMA's documented generated-request API.

    A request ID is generated by SAMA's Open Data portal after the user selects
    a table/columns. We never guess request IDs. See SAMA Statistical API user
    manual: /_layouts/15/SAMA.Internet.WCM/WebMethods.aspx/GetStatistcalById.
    """
    source_slug = "sama"
    endpoint = "https://www.sama.gov.sa/_layouts/15/SAMA.Internet.WCM/WebMethods.aspx/GetStatistcalById"

    async def fetch(self, request_id: int, language: str = "en", **kwargs) -> ConnectorResult:
        if not request_id or language not in {"en", "ar"}:
            return ConnectorResult(False, self.source_slug, error="A valid SAMA generated request ID and en/ar language are required")
        try:
            async with httpx.AsyncClient(timeout=settings.data_sync_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(
                    self.endpoint,
                    params={"id": int(request_id), "lang": f'"{language}"'},
                    headers={"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"},
                )
                response.raise_for_status()
                payload = response.json()
            has_error = bool(payload.get("HasError") or payload.get("IsError") is True)
            result = payload.get("Result") or []
            if has_error or not isinstance(result, list):
                return ConnectorResult(False, self.source_slug, error=str(payload.get("Message") or "SAMA API returned an error"))
            return ConnectorResult(True, self.source_slug, records=result, metadata={"request_id": request_id, "language": language, "url": str(response.url)})
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: source fetch failed")


class WorldBankConnector(BaseDataConnector):
    source_slug = "world-bank"
    api_base = "https://api.worldbank.org/v2"

    async def fetch(self, indicator_code: str, start_year: int = 2000, end_year: int = 2030, country: str = "SAU", **kwargs) -> ConnectorResult:
        url = f"{self.api_base}/country/{country}/indicator/{indicator_code}"
        params = {"format": "json", "per_page": 1000, "date": f"{start_year}:{end_year}", "footnote": "y"}
        try:
            async with httpx.AsyncClient(timeout=settings.data_sync_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, params=params, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
            meta = payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else {}
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list) else []
            records = []
            for row in rows:
                if row.get("value") is None:
                    continue
                records.append({
                    "date": row.get("date"),
                    "value": row.get("value"),
                    "indicator": indicator_code,
                    "indicator_name": (row.get("indicator") or {}).get("value"),
                    "country": (row.get("country") or {}).get("value"),
                    "countryiso3code": row.get("countryiso3code"),
                    "unit": row.get("unit"),
                    "obs_status": row.get("obs_status"),
                    "decimal": row.get("decimal"),
                })
            records.sort(key=lambda item: str(item.get("date") or ""))
            return ConnectorResult(True, self.source_slug, records=records, metadata={
                "url": str(response.url), "count": len(records), "lastupdated": meta.get("lastupdated"), "page": meta.get("page"), "pages": meta.get("pages")
            })
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: source fetch failed")

    async def fetch_metadata(self, indicator_code: str) -> ConnectorResult:
        url = f"{self.api_base}/indicator/{indicator_code}"
        try:
            async with httpx.AsyncClient(timeout=settings.data_sync_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url, params={"format": "json"}, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload = response.json()
            rows = payload[1] if isinstance(payload, list) and len(payload) > 1 and isinstance(payload[1], list) else []
            if not rows:
                return ConnectorResult(False, self.source_slug, error="World Bank indicator metadata was empty")
            row = rows[0]
            return ConnectorResult(True, self.source_slug, records=[row], metadata={"url": str(response.url)})
        except Exception as exc:
            return ConnectorResult(False, self.source_slug, error=f"{type(exc).__name__}: metadata fetch failed")
