# HORIZON — Energy Markets Terminal

A dashboard for tracking the crude oil and refined products complex: live
quotes, forward curves, inventories, positioning, freight, news sentiment, and
a mean-reversion paper-trading engine.

Built with a React + TypeScript frontend and a FastAPI backend that proxies and
caches public market data sources.

```
Frontend  http://localhost:5173
Backend   http://localhost:8000       API docs: http://localhost:8000/docs
```

## Features

- **Live quotes & charts** — WTI, Brent, RBOB, heating oil, gas oil, plus macro
  reference symbols, sourced from Yahoo Finance with stale-data fallback.
- **Forward curves & structure** — full forward curves with calendar spreads
  (M1-M2, M1-M6, M1-M12) and butterflies, from ICE settlement files and
  monthly futures contracts.
- **EIA inventories** — weekly petroleum stocks with a persisted snapshot so the
  dashboard loads instantly and only refreshes on demand.
- **CFTC positioning** — Commitments of Traders data for the energy contracts.
- **Baker Hughes rig count** — North America weekly and international monthly.
- **Freight** — live AIS tanker positions, density heatmap, and chokepoint counts.
- **News sentiment** — energy-filtered headlines scored locally with FinBERT.
- **Release impact** — estimates the likely Brent reaction to the upcoming
  weekly EIA crude release, from consensus/API surprise and news themes.
- **Paper trading** — a z-score mean-reversion engine on calendar spreads and
  butterflies, with an intraday backtest over full history.

## Tech stack

| Layer | Tools |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind, Recharts, MapLibre, TanStack Query, Zustand |
| Backend | FastAPI, Pydantic, httpx, pandas, PyArrow |
| ML | FinBERT (Transformers) for news sentiment |

## Project structure

```
backend/          FastAPI service
  main.py         app setup and startup
  routes.py       all HTTP endpoints, grouped by domain
  config.py       settings (env-driven)
  models.py       Pydantic response models
  services/       one module per data source
  strategy/       paper-trading engine, fair values, backtest
  curves/ seed/   ICE settlement CSVs and offline seed data

frontend/         React dashboard
  src/pages/      one file per screen
  src/components/ charts, layout, and dashboard widgets
  src/hooks/      data-fetching hooks
  src/lib/        API client, analytics, and helpers
  src/types.ts    shared types

research/         Standalone analysis behind the models (see its README)
```

## Getting started

**Windows** — run the launcher, which sets up both environments on first run:

```bash
start.bat
```

`stop.bat` shuts the servers down.

**Manual setup** — backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m uvicorn main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Configuration

The backend runs with sensible defaults and needs no keys for core features.
To enable the optional ones, copy `backend/.env.example` to `backend/.env` and
fill in what you need — an EIA API key for live inventory refreshes, and an
AISStream key for live tanker positions. Everything else uses public endpoints.

## Notes

Market data comes from public sources and is cached aggressively, with stale
snapshots served when an upstream provider is unavailable, so the dashboard
stays usable offline. This is a personal project for learning market
microstructure — not investment advice.
