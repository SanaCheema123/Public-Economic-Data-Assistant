from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"]
    for path in candidates:
        if not path.exists():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        break


_load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Public Economic Data Assistant")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./peda.db")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    jwt_secret: str = os.getenv("JWT_SECRET", "development-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
    refresh_token_days: int = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))

    # AI and answer generation. Live data does not depend on an AI key: if no
    # provider key is configured, the assistant uses the deterministic grounded
    # planner/answerer over the synchronized verified database.
    ai_provider: str = os.getenv("AI_PROVIDER", "groq").lower()
    ai_mode: str = os.getenv("AI_MODE", "live").lower()
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Live public-data synchronization. Runtime defaults are deliberately live;
    # demo/sample statistics are never seeded automatically.
    data_mode: str = os.getenv("DATA_MODE", "live").lower()
    data_sync_on_startup: bool = env_bool("DATA_SYNC_ON_STARTUP", True)
    data_background_refresh: bool = env_bool("DATA_BACKGROUND_REFRESH", True)
    data_refresh_hours: int = int(os.getenv("DATA_REFRESH_HOURS", "12"))
    gastat_headlines_enabled: bool = env_bool("GASTAT_HEADLINES_ENABLED", True)
    gastat_refresh_minutes: int = int(os.getenv("GASTAT_REFRESH_MINUTES", "30"))
    live_data_start_year: int = int(os.getenv("LIVE_DATA_START_YEAR", "2000"))
    live_data_country: str = os.getenv("LIVE_DATA_COUNTRY", "SAU")
    data_sync_timeout_seconds: float = float(os.getenv("DATA_SYNC_TIMEOUT_SECONDS", "20"))

    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
    sql_timeout_ms: int = int(os.getenv("SQL_TIMEOUT_MS", "3000"))
    sql_row_limit: int = int(os.getenv("SQL_ROW_LIMIT", "200"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "90"))
    max_request_bytes: int = int(os.getenv("MAX_REQUEST_BYTES", str(2 * 1024 * 1024)))
    auto_create_tables: bool = env_bool("AUTO_CREATE_TABLES", True)
    cookie_secure: bool = env_bool("COOKIE_SECURE", False)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def effective_ai_mode(self) -> str:
        if self.ai_mode in {"off", "disabled", "deterministic"}:
            return "deterministic"
        return "live"

    @property
    def ai_runtime(self) -> str:
        if self.effective_ai_mode != "live":
            return "deterministic"
        if self.has_groq or self.has_gemini:
            return "provider-backed"
        return "deterministic-fallback"


settings = Settings()
