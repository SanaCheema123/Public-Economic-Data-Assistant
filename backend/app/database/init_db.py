from sqlalchemy import text

from app.core.config import settings
from app.database.base import Base
from app.database.session import engine
import app.models  # noqa: F401


def init_db() -> None:
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        # pgvector is used when available for semantic retrieval. The app keeps a JSON
        # embedding fallback so SQLite tests and environments without pgvector remain functional.
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            try:
                conn.execute(text(
                    "ALTER TABLE retrieval_documents ADD COLUMN IF NOT EXISTS embedding vector(384)"
                ))
            except Exception:
                # A managed PostgreSQL service may not allow the extension. Retrieval
                # continues with deterministic lexical scoring rather than failing startup.
                pass
