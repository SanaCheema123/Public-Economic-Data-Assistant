# Public Economic Data Assistant
## المساعد الذكي للبيانات الاقتصادية العامة

A bilingual, citation-first full-stack application for Saudi economic and social data. Runtime statistics come from upstream public sources; the application does **not** seed invented demo statistics.

## Live source behavior

The backend synchronizes two real upstream sources:

1. **General Authority for Statistics (GASTAT)** — official Saudi Main Indicators from `stats.gov.sa`. Latest/current dashboard values prefer this source.
2. **World Bank Indicators API v2** — no-key Saudi (`SAU`) time series used for historical charts and as a verified fallback.

This distinction is visible in the UI: official Saudi headline cards show `OFFICIAL LIVE`, while World Bank-backed cards show `WORLD BANK LIVE`, with a clickable source and the exact published period.

If no verified upstream value is available, the application returns an unavailable/unsupported state. It does not substitute fake data.

## Docker start

```bash
cp .env.example .env
# set a strong JWT_SECRET in .env
docker compose up --build
```

Open:

- App: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Live-data status: `http://localhost:8000/api/data/status`

After login, force a fresh upstream pull with:

```http
POST /api/data/sync
```

## Python 3.11 local run without a virtual environment

Windows CMD, repository root:

```bat
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -r backend\requirements.txt

set DATABASE_URL=sqlite:///./peda.db
set DATA_MODE=live
set DATA_SYNC_ON_STARTUP=true
set DATA_BACKGROUND_REFRESH=true
set GASTAT_HEADLINES_ENABLED=true
set GASTAT_REFRESH_MINUTES=30
set DATA_REFRESH_HOURS=12
set AI_MODE=live
set JWT_SECRET=local-development-secret-change-this-123456789
set FRONTEND_URL=http://localhost:5173
set BACKEND_URL=http://localhost:8000

cd backend
py -3.11 -m alembic upgrade head
py -3.11 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Second terminal:

```bat
cd frontend
npm install
npm run dev
```

### Verify that the data is actually live

Open:

```text
http://localhost:8000/api/data/status
```

Look for:

```json
{
  "mode": "live",
  "official_headlines_ready": true,
  "sources": {
    "gastat": {"ready": true, "official": true},
    "world_bank": {"ready": true}
  }
}
```

The exact timestamps/counts depend on upstream availability.

If `official_headlines_ready` is `false`, call `POST /api/data/sync` and inspect its `gastat.error` field. The dashboard will clearly show that World Bank fallback data is being used rather than pretending it is GASTAT data.

## AI providers

Live public data does not require an AI key. Groq/Gemini are used only for language/query planning when configured; all factual values still come from verified database rows.

Groq:

```env
AI_MODE=live
AI_PROVIDER=groq
GROQ_API_KEY=your_key
```

Gemini:

```env
AI_MODE=live
AI_PROVIDER=gemini
GEMINI_API_KEY=your_key
```

If providers fail, grounded deterministic retrieval/Text-to-SQL remains available.

## Data provenance and safety

- Numeric responses come from safe SQL over synchronized verified rows.
- Citations include indicator, dataset, period, source and URL.
- Latest/current questions prefer official GASTAT headline observations.
- Historical/trend questions prefer consistent World Bank time series.
- Generated SQL remains SELECT-only and is validated against the allowlisted schema.
- Unsupported statistics are not guessed.

## Tests

Backend:

```bash
cd backend
pytest -q
```

Expected for this revision:

```text
25 passed
```

Frontend:

```bash
cd frontend
npm install
npm test
npm run build
```

E2E after the stack is running:

```bash
npm install
npx playwright install chromium
npm run test:e2e
```

## Production notes

- Use PostgreSQL + pgvector and TLS.
- Use a strong `JWT_SECRET`; set `COOKIE_SECURE=true` behind HTTPS.
- Keep live synchronization enabled.
- For multi-replica deployment, run upstream synchronization from one scheduled worker/instance.
- Monitor `/health` and `/api/data/status`.
- Keep Groq/Gemini keys server-side only.

## Windows: quickest local start (Python 3.11, no virtual environment)

The project now includes PowerShell launchers that install/check the backend dependencies before starting the server:

```powershell
.\scripts\run-backend-windows.ps1
```

In a second PowerShell window:

```powershell
.\scripts\run-frontend-windows.ps1
```

If Vite reports `ECONNREFUSED` for `/api/*`, FastAPI is not listening on port 8000. Read the backend console first. The local Vite proxy intentionally targets `http://127.0.0.1:8000` to avoid Windows localhost IPv6/IPv4 ambiguity.

The GASTAT connector no longer requires BeautifulSoup at import time; it uses Python's standard-library HTML parser, so a missing `bs4` package cannot crash the backend.
