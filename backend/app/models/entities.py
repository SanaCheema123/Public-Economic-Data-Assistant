from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    theme_preference: Mapped[str] = mapped_column(String(16), default="light", nullable=False)
    notification_preference: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Session(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(240))
    name_ar: Mapped[str] = mapped_column(String(240))
    organization: Mapped[str] = mapped_column(String(240))
    url: Mapped[str] = mapped_column(String(1000))
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
    update_frequency: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(120), default="Saudi Arabia")
    reliability_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    source_type: Mapped[str] = mapped_column(String(32), default="official")
    last_synchronization_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="source")


class Dataset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "datasets"
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(240))
    name_ar: Mapped[str] = mapped_column(String(240))
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000))
    update_frequency: Mapped[str | None] = mapped_column(String(80))
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    last_updated: Mapped[date | None] = mapped_column(Date)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[Source] = relationship(back_populates="datasets")
    indicators: Mapped[list["Indicator"]] = relationship(back_populates="dataset")


class Indicator(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "indicators"
    indicator_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(240), index=True)
    name_ar: Mapped[str] = mapped_column(String(240), index=True)
    description_en: Mapped[str] = mapped_column(Text)
    description_ar: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(String(80))
    frequency: Mapped[str] = mapped_column(String(80))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id", ondelete="RESTRICT"), index=True)
    country: Mapped[str] = mapped_column(String(120), default="Saudi Arabia")
    category: Mapped[str] = mapped_column(String(100), index=True)
    last_updated: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")
    dataset: Mapped[Dataset] = relationship(back_populates="indicators")
    values: Mapped[list["IndicatorValue"]] = relationship(back_populates="indicator", cascade="all, delete-orphan")


class IndicatorValue(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "indicator_values"
    indicator_id: Mapped[str] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str | None] = mapped_column(String(160), index=True)
    sector: Mapped[str | None] = mapped_column(String(160), index=True)
    dimension_json: Mapped[dict] = mapped_column(JSON, default=dict)
    indicator: Mapped[Indicator] = relationship(back_populates="values")
    __table_args__ = (Index("ix_indicator_value_lookup", "indicator_id", "date", "region", "sector"),)


class DataDimension(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "data_dimensions"
    indicator_id: Mapped[str] = mapped_column(ForeignKey("indicators.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    value: Mapped[str] = mapped_column(String(240))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Query(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "queries"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    question: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(8))
    intent: Mapped[str | None] = mapped_column(String(80))
    query_type: Mapped[str | None] = mapped_column(String(80))
    generated_sql: Mapped[str | None] = mapped_column(Text)
    sql_params: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    ai_provider: Mapped[str | None] = mapped_column(String(32))
    latency_ms: Mapped[int | None] = mapped_column(Integer)


class QueryResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "query_results"
    query_id: Mapped[str] = mapped_column(ForeignKey("queries.id", ondelete="CASCADE"), index=True)
    indicator_id: Mapped[str | None] = mapped_column(ForeignKey("indicators.id", ondelete="SET NULL"), index=True)
    answer_en: Mapped[str] = mapped_column(Text)
    answer_ar: Mapped[str] = mapped_column(Text)
    data_json: Mapped[list] = mapped_column(JSON, default=list)
    chart_json: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[str] = mapped_column(String(32), default="medium")
    unsupported: Mapped[bool] = mapped_column(Boolean, default=False)


class Citation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "citations"
    query_result_id: Mapped[str] = mapped_column(ForeignKey("query_results.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), index=True)
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id", ondelete="SET NULL"), index=True)
    indicator_id: Mapped[str | None] = mapped_column(ForeignKey("indicators.id", ondelete="SET NULL"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(1000))
    period: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Collection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "collections"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_collection_user_name"),)


class SavedItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "saved_items"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_result_id: Mapped[str | None] = mapped_column(ForeignKey("query_results.id", ondelete="CASCADE"), index=True)
    collection_id: Mapped[str | None] = mapped_column(ForeignKey("collections.id", ondelete="SET NULL"), index=True)
    item_type: Mapped[str] = mapped_column(String(40), default="answer", index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SavedChart(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "saved_charts"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_result_id: Mapped[str | None] = mapped_column(ForeignKey("query_results.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    chart_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300), default="New conversation")
    language: Mapped[str] = mapped_column(String(8), default="en")


class ChatMessage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "chat_messages"
    chat_session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(24))
    content: Mapped[str] = mapped_column(Text)
    query_result_id: Mapped[str | None] = mapped_column(ForeignKey("query_results.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Insight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "insights"
    category: Mapped[str] = mapped_column(String(100), index=True)
    title_en: Mapped[str] = mapped_column(String(300))
    title_ar: Mapped[str] = mapped_column(String(300))
    summary_en: Mapped[str] = mapped_column(Text)
    summary_ar: Mapped[str] = mapped_column(Text)
    indicator_ids: Mapped[list] = mapped_column(JSON, default=list)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified")


class AuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "audit_logs"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(160), index=True)
    request_id: Mapped[str | None] = mapped_column(String(80), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class APIUsage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "api_usage"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str] = mapped_column(String(160))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RetrievalDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "retrieval_documents"
    kind: Mapped[str] = mapped_column(String(40), index=True)
    ref_id: Mapped[str] = mapped_column(String(36), index=True)
    title_en: Mapped[str] = mapped_column(String(300))
    title_ar: Mapped[str] = mapped_column(String(300))
    content_en: Mapped[str] = mapped_column(Text)
    content_ar: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    embedding_json: Mapped[list] = mapped_column(JSON, default=list)


ALL_MODELS = [
    User, Session, Source, Dataset, Indicator, IndicatorValue, DataDimension,
    Query, QueryResult, Citation, SavedItem, SavedChart, Collection,
    ChatSession, ChatMessage, Insight, AuditLog, APIUsage, RetrievalDocument,
]
