---
title: Horizon Backend
emoji: ⚡
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# HORIZON Market Data API

Thin FastAPI proxy + in-memory cache over Yahoo Finance for the HORIZON energy terminal.

## Why a backend?
Yahoo's data endpoints don't send CORS headers and keyed providers (EIA, weather,
news) can't expose secrets in the browser. This service centralizes upstream calls,
normalizes responses to the frontend's `Commodity` shape (camelCase), and caches
snapshots to avoid rate limits.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive docs: http://localhost:8000/docs

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/api/quotes?group=core` | Snapshot for a group (`core`, `macro`, `products`, `all`) |
| GET | `/api/quote/{id}` | Single quote (e.g. `brent`, `wti`, `henryhub`) |
| GET | `/api/history/{id}?range=3mo` | Intraday/daily series for charts |

`range` ∈ `1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y`.

## Coverage
Yahoo provides: Brent, WTI, Henry Hub, TTF, VIX, DXY, S&P 500, US 10Y, Gold, Copper,
RBOB, Heating Oil. **LNG JKM is not on Yahoo** — it stays on placeholder data until
we add a dedicated source.

## Notes
- In-memory cache only (single process). For production, front it with a real proxy
  or move the cache to Redis and add scheduled polling.
