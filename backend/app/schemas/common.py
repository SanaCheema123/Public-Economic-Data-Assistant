from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CitationOut(BaseModel):
    id: str | None = None
    title: str
    source_name: str
    source_name_ar: str | None = None
    dataset_name: str
    dataset_name_ar: str | None = None
    indicator_name: str | None = None
    indicator_name_ar: str | None = None
    period: str | None = None
    url: str
    verification_status: str = "unverified"


class IndicatorSummary(BaseModel):
    id: str
    indicator_id: str
    name: str
    name_ar: str
    unit: str
    category: str
    description: str | None = None
    description_ar: str | None = None
    verification_status: str = "unverified"


class ChartSpec(BaseModel):
    type: Literal["line", "bar", "area", "pie", "donut", "grouped_bar"] = "line"
    title: str = ""
    title_ar: str = ""
    x: list[Any] = Field(default_factory=list)
    y: list[float] = Field(default_factory=list)
    series: list[dict[str, Any]] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)
    x_label: str | None = None
    y_label: str | None = None


class ChatResponse(BaseModel):
    query_id: str
    chat_session_id: str
    result_id: str
    answer: str
    answer_ar: str
    language: str
    indicator: IndicatorSummary | None = None
    data: list[dict[str, Any]] = Field(default_factory=list)
    chart: ChartSpec | None = None
    citations: list[CitationOut] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "unsupported"] = "medium"
    unsupported: bool = False
    generated_at: datetime
    sql_preview: str | None = None


class SourceOut(ORMModel):
    id: str
    slug: str
    name_en: str
    name_ar: str
    organization: str
    url: str
    description_en: str
    description_ar: str
    update_frequency: str | None
    country: str
    reliability_metadata: dict[str, Any]
    source_type: str
    last_synchronization_date: datetime | None
    datasets: list[dict[str, Any]] = Field(default_factory=list)


class DatasetOut(ORMModel):
    id: str
    source_id: str
    slug: str
    name_en: str
    name_ar: str
    description_en: str
    description_ar: str
    source_url: str
    update_frequency: str | None
    verification_status: str
    last_updated: date | None
    metadata_json: dict[str, Any]
