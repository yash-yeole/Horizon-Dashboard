# HORIZON — Energy Markets Intelligence Terminal
## Complete Project Handoff & Continuation Document

> **Read this first.** This single document is meant to bring any new Claude session (or developer)
> fully up to speed with zero prior context. It explains *what* the project is, *why* every decision
> was made, *how* it was built, the *complete architecture*, *how to run it*, what is *live vs.
> placeholder*, *every bug already fixed*, and the *prioritized backlog*. Everything in this project —
> all code, files, backend, and tooling — was generated from scratch in a single Claude Code session.

- **Project name:** HORIZON (originally NEXUS, renamed)
- **Location:** `D:\Dashboard_FF`
- **Owner:** Yash Y — sakshiyeole210@gmail.com
- **Generated:** 31 May 2026
- **State:** Frontend complete (13 pages) + FastAPI backend serving live Yahoo Finance data; live price charts with a commodity selector working on 4 pages.

---

## TABLE OF CONTENTS
1. What HORIZON Is
2. The Full Build Story (chronological)
3. Tech Stack & Why
4. Complete Folder Structure (every file, annotated)
5. Design System
6. Frontend Architecture
7. The 13 Pages
8. Backend Architecture & API
9. Data Flow (end-to-end)
10. Live vs. Placeholder Data
11. How to Run (with all the gotchas we hit)
12. Every Issue Already Fixed
13. Conventions
14. Prioritized Backlog
15. Quick-Start for the Next Claude

---

## 1. What HORIZON Is

HORIZON is an **institutional-grade Energy Markets Intelligence Dashboard** — a "trader workstation"
inspired by Bloomberg Terminal, Kpler, TradingView, Vortexa, and Refinitiv Eikon, but with a cleaner,
modern, dark UI. It is built for quant analysts, commodity traders, and energy researchers to monitor:

Crude oil, refined products, natural gas, LNG, power, macro indicators, freight & shipping, weather,
inventories, spreads, curves, and news sentiment.

Design philosophy: **"High information density without clutter — terminal meets modern SaaS."**

It began as a **frontend-only** build (explicitly no backend at first). Later the user asked to connect
real data, starting with Yahoo Finance, which required adding a **Python FastAPI backend** (because
Yahoo has no CORS headers and future keyed APIs can't expose secrets in the browser).

---

## 2. The Full Build Story (chronological)

This is the order things were built, so the next session understands how we got here:

1. **Scaffolding** — Vite + React + TS project created under `energy-dashboard/`. Installed Tailwind v4,
   Framer Motion, Recharts, Lucide, Zustand, React Router, Radix primitives, TanStack Table.
   Configured the `@/` path alias and a dark theme token system in `index.css`.
2. **Data layer** — built realistic dummy data in `src/data/` (`market.ts`, `series.ts`, `content.ts`)
   plus generators in `lib/utils.ts`.
3. **Design system** — reusable primitives: `Card`, `Badge`, and an `index.tsx` barrel of
   `Button/Tabs/StatusDot/Progress/Skeleton/Tooltip/FilterBar/SectionTitle`.
4. **Charts** — reusable Recharts wrappers: `Sparkline`, `AreaChartPro`, `MultiLineChart`, `CurveChart`,
   `VolumeChart`, `SpreadBars`, `BarChartPro`, a correlation `Heatmap`, and a custom `ChartTooltip`.
5. **Layout** — `AppShell` (sidebar + topbar + ticker + animated routed content), collapsible `Sidebar`,
   `Topbar` (search, market status, watchlist, live UTC clock, profile), and a scrolling `Ticker` tape.
   Zustand `useUIStore` holds sidebar/watchlist state; `useClock` drives the UTC clock.
6. **Widgets** — `MetricCard`, `DataTable`, `ChartCard`, `PageHeader`, dashboard `Panels`
   (news/movers/calendar/alerts/spreads/shipping), `NewsModal`, `CommodityBoard`, `MapPlaceholder`.
7. **Pages** — all 13 built with dummy data (see section 7).
8. **Routing & entry** — `App.tsx` routes, `main.tsx` root.
9. **Rename** — NEXUS → **HORIZON** (sidebar wordmark, `index.html` title/meta). Considered names:
   Horizon, Meridian, Flux, Cortex — user chose **Horizon**.
10. **Profile rename** — "S. Yeole / Sakshi Yeole" (initials SY) → **Yash Y** (initials YY) in Topbar
    and Settings.
11. **Backend decision** — user asked to connect Yahoo Finance, then explicitly asked for a backend.
    Chosen via Q&A: **Python FastAPI**, **thin proxy + in-memory cache** scope.
12. **Backend build** — full FastAPI service under `backend/` (see section 8). Verified live: Brent,
    WTI, Henry Hub, TTF, VIX, DXY all returning real numbers.
13. **Frontend ↔ backend wiring** — Vite `/api` proxy → `localhost:8000`; React Query hooks
    (`useQuotes`); `mergeQuotes` overlays live data onto static cards by id; `QueryClientProvider` added
    to `main.tsx`. Dashboard hero cards went live with a "Yahoo Live / Offline" badge.
14. **Live charts** — built `LivePriceChart` (price + history from the same backend) with a **commodity
    selector dropdown** and **Yahoo-matching range tabs** (1D/5D/1M/6M/1Y/5Y). Rolled onto Dashboard,
    Crude, Gas, Macro.
15. **Bug fixes** — dropdown clipping (truncate overflow) and selection-not-registering (onBlur race).
    See section 12.
16. **Tooling** — `start.bat` (launch both servers) and `stop.bat` (kill by port). Handoff docs (this
    file + PDF + source ZIP).

---

## 3. Tech Stack & Why

| Layer | Technology | Why |
|---|---|---|
| Frontend framework | React 19 + Vite + TypeScript | Fast HMR, modern, typed |
| Styling | TailwindCSS v4 (`@tailwindcss/vite`) | Utility-first; v4 uses CSS `@theme` tokens (no JS config) |
| Charts | Recharts 3 | Declarative, responsive, composable |
| Animation | Framer Motion | Sidebar springs, page transitions, card hovers |
| Icons | Lucide React | Clean line icons; referenced by string name in nav |
| UI state | Zustand | Tiny, no boilerplate (sidebar collapse, watchlist) |
| Server state | TanStack React Query | Caching, auto-refetch, loading/error states for live data |
| Routing | React Router DOM 7 | Standard SPA routing |
| Backend | Python FastAPI + Uvicorn | Async, auto OpenAPI docs; user chose Python for future quant work |
| HTTP client | httpx (async) | Concurrent Yahoo fetches |
| Validation/serialization | Pydantic v2 | camelCase output via `alias_generator` → maps to TS types |
| Data source | Yahoo Finance v8 chart endpoint | Free, no API key, gives quote + intraday series in one call |

**Note on TailwindCSS v4:** there is no `tailwind.config.js`. Theme tokens live in `src/index.css`
under an `@theme { ... }` block. The Vite plugin `@tailwindcss/vite` is registered in `vite.config.ts`.

---

## 4. Complete Folder Structure (every source file, annotated)

```
D:\Dashboard_FF\
├── start.bat                       One-click: opens backend + frontend terminals
├── stop.bat                        Kills processes on ports 8000 / 5173 / 5174
├── HANDOFF.md                      This document
├── HORIZON_Project_Handoff.pdf     PDF version of the handoff
├── HORIZON_source.zip              Zipped source (no node_modules/.venv/dist)
├── .claude/launch.json             Preview launcher config
│
├── backend\                        FastAPI service
│   ├── .venv\                      Python virtual environment (NOT in zip)
│   ├── requirements.txt            fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings
│   ├── .env.example                Optional HORIZON_* env overrides
│   ├── README.md                   Backend-specific readme
│   └── app\
│       ├── __init__.py
│       ├── main.py                 FastAPI app, CORS middleware, /health, includes router
│       ├── config.py               Settings (env prefix HORIZON_), Yahoo URL/UA, cache TTL, CORS origins
│       ├── symbols.py              SymbolDef dataclass + CORE/MACRO/PRODUCTS groups + BY_ID + GROUPS
│       ├── models.py               CamelModel base, Quote, QuotesResponse, HistoryPoint, HistoryResponse
│       ├── cache.py                TTLCache (get / get_stale / set)
│       ├── services\
│       │   ├── __init__.py
│       │   └── yahoo.py            Async Yahoo client: fetch_quotes(), fetch_history(), parsing
│       └── routers\
│           ├── __init__.py
│           └── quotes.py           /api/quotes, /api/quote/{id}, /api/history/{id}; cache + stale fallback
│
└── energy-dashboard\               React frontend
    ├── index.html                  Loads Inter + JetBrains Mono fonts; title "HORIZON · Energy Terminal"
    ├── package.json                Scripts: dev / build / lint / preview
    ├── vite.config.ts              @ alias + server.proxy '/api' -> http://localhost:8000
    ├── tsconfig*.json              TS config (baseUrl removed; paths '@/*' -> src/*)
    ├── eslint.config.js
    ├── public\                     favicon.svg, icons.svg
    └── src\
        ├── main.tsx                Root: QueryClientProvider + App
        ├── App.tsx                 Routes for all 13 pages inside <AppShell/>
        ├── index.css               Tailwind v4 @theme tokens, scrollbar, .mono, .skeleton, .pulse-dot
        ├── components\
        │   ├── layout\
        │   │   ├── AppShell.tsx     Sidebar + Topbar + Ticker + <Outlet/> with AnimatePresence
        │   │   ├── Sidebar.tsx      Collapsible, animated active indicator, icon-by-name from lucide
        │   │   ├── Topbar.tsx       Search, market status dots, watchlist select, UTC clock, profile (YY)
        │   │   └── Ticker.tsx       Infinite-scroll price tape (CSS keyframes)
        │   ├── ui\
        │   │   ├── Card.tsx         Card, CardHeader(title/subtitle/action/icon), CardBody, MotionCard
        │   │   ├── Badge.tsx        Badge + SentimentBadge + ImportanceBadge
        │   │   └── index.tsx        Button, Tabs, StatusDot, Skeleton, Tooltip, Progress, FilterBar, SectionTitle
        │   ├── charts\
        │   │   ├── index.tsx        Sparkline, AreaChartPro, MultiLineChart, CurveChart, VolumeChart, SpreadBars, BarChartPro
        │   │   ├── Heatmap.tsx      CorrelationHeatmap (color-scaled grid)
        │   │   └── ChartTooltip.tsx Custom dark tooltip (Recharts v3 compatible)
        │   └── widgets\
        │       ├── MetricCard.tsx       Hero metric card w/ sparkline + change badge
        │       ├── DataTable.tsx        Generic typed table (Column<T> render fns)
        │       ├── ChartCard.tsx        Chart container: title/subtitle/leftControl/rightMeta/range tabs
        │       ├── PageHeader.tsx       Page title + live status dot + actions
        │       ├── Panels.tsx           NewsFeed, MarketMovers, EconomicCalendar, AlertsSummary, SpreadMonitor, ShippingCongestion
        │       ├── NewsModal.tsx        Animated article preview modal
        │       ├── CommodityBoard.tsx   Live-style commodity table (uses DataTable)
        │       ├── MapPlaceholder.tsx   Stylized SVG map w/ animated points & routes
        │       └── LivePriceChart.tsx   ★ LIVE chart: commodity dropdown + Yahoo range tabs + live price/series
        ├── pages\                   Dashboard, Crude, Products, Gas, LNG, Freight, Macro, Weather,
        │                            Inventories, News, Analytics, Alerts, Settings
        ├── hooks\
        │   ├── useClock.ts          Live UTC HH:MM:SS
        │   └── useQuotes.ts         ★ React Query: useQuotes, useQuote, useHistory + mergeQuotes/quoteToCommodity
        ├── services\
        │   └── api.ts               fetch wrapper: quotes(), quote(), history()
        ├── store\
        │   └── useUIStore.ts        Zustand: sidebarCollapsed, watchlist, searchOpen
        ├── constants\
        │   ├── index.ts             COLORS, CHART_COLORS, NAV_ITEMS, MARKET_HOURS
        │   └── symbols.ts           ★ Yahoo symbol map (mirrors backend symbols.py)
        ├── data\
        │   ├── market.ts            HERO_METRICS, CRUDE_GRADES, PRODUCTS, TOP_GAINERS/LOSERS
        │   ├── series.ts            time series, curves, SPREADS, correlation matrix
        │   └── content.ts           NEWS, INVENTORIES, FREIGHT_RATES, PORT_CONGESTION, WEATHER_STATIONS, ALERTS, ECONOMIC_CALENDAR
        ├── types\
        │   ├── index.ts             Commodity, NewsItem, InventoryData, FreightRate, WeatherStation, AlertItem, SpreadData, CurvePoint, CorrelationEntry, NavItem
        │   └── api.ts               ApiQuote, QuotesResponse, HistoryPoint, HistoryResponse, QuoteGroup
        └── lib\
            └── utils.ts             cn(), formatters (price/change/percent/compact/volume), generators (sparkline/timeSeries)
```

★ = files central to the live-data feature.

---

## 5. Design System

**Palette** (from `constants/index.ts` and `index.css` `@theme`):
- Backgrounds: `#0a0b0d` (app), `#0f1117` (surface), `#161820`, `#1c1e27`
- Borders: `#1f2230` (default), `#2a2d3e` (strong)
- Accent blue `#2563eb`; up-green `#10b981`; down-red `#ef4444`; amber `#f59e0b`; purple `#8b5cf6`; cyan `#06b6d4`
- Text: primary `#e2e8f0`, secondary `#94a3b8`, muted `#475569`
- Chart series palette: `CHART_COLORS` (blue, green, amber, red, purple, cyan, pink, teal)

**Typography:** Inter (UI) + JetBrains Mono (all numbers — apply class `mono`). Loaded via Google Fonts
in `index.html`. Base font-size 13px, dense spacing.

**Helpers in index.css:** `.mono`, `.skeleton` (shimmer), `.pulse-dot` (live indicator pulse).

**Reusable component contracts:**
- `Card` + `CardHeader({title, subtitle, action, icon})` — `title`/`subtitle` accept `ReactNode`.
- `ChartCard({title?, subtitle?, leftControl?, rightMeta?, ranges?, defaultRange?, range?, onRangeChange?})`
  — supports both uncontrolled (defaultRange) and controlled (range + onRangeChange) modes.
- `Badge` variants: green/red/amber/blue/purple/cyan/neutral.
- `DataTable<T>` with `Column<T> = { key, header, align?, render?(row) }`.

---

## 6. Frontend Architecture

- **Entry:** `main.tsx` wraps `<App/>` in `QueryClientProvider` (retry 1, no refetch-on-focus).
- **Routing:** `App.tsx` → `<BrowserRouter>` with all pages nested under `<AppShell/>` (layout route).
- **Layout:** `AppShell` renders `Sidebar` + `Topbar` + `Ticker` + an `<Outlet/>` animated by
  `AnimatePresence` keyed on pathname.
- **State:** UI-only state in Zustand (`useUIStore`). Server/market state in React Query (`useQuotes.ts`).
- **Live data merge pattern:** static dummy arrays (e.g. `HERO_METRICS`) remain the baseline; `mergeQuotes`
  overlays live quotes by matching `id`. This keeps unsupported instruments (JKM) working as fallback and
  means the UI never breaks if the backend is down.

---

## 7. The 13 Pages

| Route | Page | Highlights | Data |
|---|---|---|---|
| `/` | Dashboard | Hero metrics (7), LivePriceChart, cross-commodity, curve, correlation, news, alerts, movers, calendar, inventory/weather/shipping snapshots | Hero + main chart LIVE; rest dummy |
| `/crude` | Crude Oil | Grade cards, LivePriceChart (Brent + WTI), forward curve, spreads, board | 2 charts LIVE |
| `/products` | Products | Crack spreads, refinery utilization, product board | Dummy |
| `/gas` | Natural Gas | LivePriceChart (Henry Hub + TTF), storage levels, curve | 2 charts LIVE |
| `/lng` | LNG | JKM card, cargo tracking table, liquefaction util | Dummy (Yahoo has no JKM) |
| `/freight` | Freight | Vessel map, tanker rates, congestion, freight spreads | Dummy |
| `/macro` | Macro | Indicator cards, LivePriceChart (DXY), correlation heatmap, calendar | DXY chart LIVE |
| `/weather` | Weather | Station cards, storm tracker map, HDD/CDD, severity | Dummy |
| `/inventories` | Inventories | Weekly change cards, EIA-style stocks, PADD utilization, map | Dummy (EIA pending) |
| `/news` | News | Filterable timeline, sentiment stats, article modal | Dummy |
| `/analytics` | Analytics | Draggable panels (Framer Reorder), strategy notes, volatility | Dummy |
| `/alerts` | Alerts | Interactive feed (mark-read/delete), filters, stats | Dummy (local state) |
| `/settings` | Settings | Tabbed (profile/notifications/appearance/data/regional/security), toggles | Profile = Yash Y |

---

## 8. Backend Architecture & API

**Purpose:** thin proxy + in-memory cache over Yahoo Finance. Centralizes upstream calls, normalizes to
the frontend's `Commodity` shape (camelCase), caches snapshots (~20s TTL) to avoid rate limits, and falls
back to the last cached snapshot (flagged `stale`) on upstream failure.

**Why it exists:** (1) Yahoo's endpoints send no CORS headers, so the browser can't call them directly;
(2) future keyed providers (EIA, weather, news) must keep secrets server-side.

**Run:**
```
cd D:\Dashboard_FF\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
Docs (Swagger UI): http://localhost:8000/docs

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/health` | `{status: "ok"}` |
| GET | `/api/quotes?group=core` | Snapshot for a group. group ∈ core/macro/products/all |
| GET | `/api/quote/{id}` | Single quote by id |
| GET | `/api/history/{id}?range=1mo` | Time series for charts |

**History ranges:** `1d, 5d, 1mo, 6mo, 1y, 5y` (each maps to a sensible interval server-side).

**Symbol map (`backend/app/symbols.py`, mirrored in `frontend src/constants/symbols.ts`):**

| id | Yahoo | Name | Unit / Ccy | Group |
|---|---|---|---|---|
| brent | BZ=F | Brent Crude | bbl / USD | core |
| wti | CL=F | WTI Crude | bbl / USD | core |
| henryhub | NG=F | Henry Hub | MMBtu / USD | core |
| ttf | TTF=F | TTF Gas | MWh / EUR | core |
| vix | ^VIX | VIX | idx | core |
| dxy | DX-Y.NYB | DXY | idx | core |
| sp500 | ^GSPC | S&P 500 | idx | macro |
| ust10y | ^TNX | US 10Y Yield | % | macro |
| gold | GC=F | Gold | oz / USD | macro |
| copper | HG=F | Copper | lb / USD | macro |
| rbob | RB=F | RBOB Gasoline | gal / USD | products |
| heatoil | HO=F | Heating Oil | gal / USD | products |

**⚠ LNG JKM is NOT on Yahoo** — it remains placeholder data everywhere until a dedicated source is added.

**Response shape (`Quote`):** `id, yahooSymbol, name, price, change, changePct, high, low, prevClose,
volume, currency, unit, category, sparkline[], marketTime, stale`.

**Config (`backend/app/config.py`):** env vars prefixed `HORIZON_` (e.g. `HORIZON_CACHE_TTL`,
`HORIZON_REQUEST_TIMEOUT`). CORS origins: `http://localhost:5173`, `http://127.0.0.1:5173` (add 5174 if
Vite falls back to that port).

---

## 9. Data Flow (end-to-end)

```
Browser (React Query) ──fetch /api/...──► Vite dev proxy ──► FastAPI :8000 ──httpx──► Yahoo Finance v8
        ▲                                                          │
        └───────────────── JSON (camelCase Quote/History) ◄────────┘
```

- `src/services/api.ts` — `getJson` wrapper; base URL = `VITE_API_BASE_URL` or `''` (use proxy).
- `src/hooks/useQuotes.ts`:
  - `useQuotes(group)` — 30s auto-refetch, staleTime 15s.
  - `useQuote(id, group)` — selects one quote out of the cached group query.
  - `useHistory(id, range)` — chart series, staleTime 60s.
  - `quoteToCommodity(q)` — DTO → `Commodity` card shape.
  - `mergeQuotes(statics, live)` — overlay by id (static = fallback).
- `LivePriceChart.tsx` — uses `useQuote` (header price) + `useHistory` (series) so the number and the line
  always come from the **same source**. Dropdown switches `id`; range tabs switch the Yahoo range.

---

## 10. Live vs. Placeholder Data

| Area | Status |
|---|---|
| Dashboard hero metric cards | **LIVE** (core group); JKM static |
| Main price charts (Dashboard, Crude×2, Gas×2, Macro) | **LIVE** via LivePriceChart |
| Commodity selector + range tabs | **LIVE**, working |
| Forward curve charts | Placeholder |
| Cross-commodity / rebased multi-line | Placeholder |
| Spreads, correlation heatmap | Placeholder |
| Inventories / storage | Placeholder (needs EIA API key) |
| News, Weather, Freight, Alerts, Analytics | Placeholder (static dummy) |
| Commodity board tables, LNG cargo | Static dummy |

---

## 11. How to Run (with all the gotchas we actually hit)

### Easiest — one-click launchers (project root)
- Double-click **`start.bat`** → opens 2 windows (backend :8000, frontend :5173).
- Double-click **`stop.bat`** → frees ports 8000/5173/5174 (kills by port, not by process name).

### Manual — Backend (Terminal 1)
```
cd D:\Dashboard_FF\backend
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### Manual — Frontend (Terminal 2)
```
cd D:\Dashboard_FF\energy-dashboard
npm run dev
```
Open **http://localhost:5173** (or 5174 if 5173 is busy).

### Gotchas encountered (and their fixes)
1. **PowerShell execution policy** blocks `.venv\Scripts\Activate.ps1`
   → call `.venv\Scripts\python.exe` directly (as above), **or** run once:
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
2. **`npm` not recognized** — Node is installed at `C:\Program Files\nodejs` but not on PATH.
   Permanent fix (run once, then reopen terminal):
   `[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";C:\Program Files\nodejs", "User")`
   (`start.bat` already prepends Node to PATH for its frontend window.)
3. **`node not recognized` even after npm ran** — same PATH issue; the permanent fix only applies to
   terminals opened *after* it runs.
4. **Port already in use** — leftover uvicorn/vite from a previous session. Use `stop.bat` or kill by port.

**The backend must be running for live data.** If down, the dashboard still loads with an amber
"Offline / cached" badge using static numbers.

### First-time setup (if cloning fresh from the ZIP — these dirs are NOT included)
```
# Backend
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Frontend
cd ../energy-dashboard
npm install
```

---

## 12. Every Issue Already Fixed (don't re-debug these)

1. **tsconfig `baseUrl` deprecation** (TS 7 warning) → removed `baseUrl`, kept `paths`.
2. **Recharts v3 tooltip typing** — `TooltipProps` no longer exposes `payload/label` the same way →
   `ChartTooltip` now defines its own props interface.
3. **Unused imports** after refactors → cleaned (e.g. AreaChartPro/brentSeries when charts went live).
4. **NEXUS → HORIZON** rename across Sidebar + index.html.
5. **Profile rename** S. Yeole/SY → Yash Y/YY in Topbar + Settings (avatar, name, full-name field).
6. **Black preview screen** — was a stale preview tab after heavy HMR; clean reload fixed it (not a code bug).
7. **Commodity dropdown showed only the trigger** — the selector was passed as ChartCard `title`, which
   `CardHeader` renders inside an `<h3 class="truncate">` (`overflow:hidden`) that **clipped the dropdown**.
   Fix: pass the selector via the `leftControl` slot instead, and made ChartCard `title` optional.
8. **Dropdown selection didn't register on real clicks** — options used `onClick`, but the trigger's
   `onBlur` closed the menu before the click resolved (synthetic `.click()` in tests masked it).
   Fix: select on **`onMouseDown`** (fires before blur) + a **click-outside listener** via `ref`/`useEffect`.
9. **Range tabs made consistent with Yahoo** — changed from `1D/1W/1M/3M/1Y` to Yahoo's
   `1D/5D/1M/6M/1Y/5Y`, mapped to `1d/5d/1mo/6mo/1y/5y`.

---

## 13. Conventions

- Path alias `@` → `src/` (configured in both `vite.config.ts` and `tsconfig.app.json`).
- All numbers use the `mono` class (JetBrains Mono).
- Verify any change with: `npx tsc -b --noEmit` then `npm run build` (in `energy-dashboard`).
- Backend env vars prefixed `HORIZON_`; see `backend/.env.example`.
- Lucide icons are referenced by **string name** in `NAV_ITEMS` and resolved dynamically in `Sidebar.tsx`.
- Keep the live-merge pattern: never remove the static fallback arrays — they keep the UI resilient.

---

## 14. Prioritized Backlog

**High priority**
1. **Cross-Commodity multi-line chart → live.** Fetch several Yahoo series via `useHistory`, rebase each
   to 100 at the start of the window, render with `MultiLineChart`. (Most-requested natural next step.)
2. **Sparkline fallback:** when the `1d` intraday array is empty (market closed), fall back to `5d` for
   the metric-card sparklines so they're never flat.
3. **EIA data source** for Inventories/Storage — needs a free EIA API key; route it through the backend
   (this is exactly why the backend exists). Add an `eia.py` service + `/api/inventories` endpoint.

**Medium / later**
4. Forward-curve charts from a real futures-strip source.
5. Light-theme toggle (the Topbar sun button is currently static).
6. Code-split the bundle (main chunk > 500 kB warning) via dynamic `import()`.
7. Real news/weather/freight feeds (most need API keys → backend).
8. Persist history in a DB (Postgres/SQLite) if backtesting/longer history is needed.
9. WebSocket or shorter polling for true real-time ticks.

---

## 15. Quick-Start for the Next Claude

1. Read this file top-to-bottom (you now have full context).
2. Ensure the project folder is present (the ZIP excludes `node_modules`, `.venv`, `dist` — run the
   "First-time setup" in section 11 if those are missing).
3. Run `start.bat`, open http://localhost:5173, confirm the green **"Yahoo Live"** badge on the Dashboard.
4. Pick a backlog item — the most natural continuation is **#1 (live Cross-Commodity chart)** or
   **#3 (EIA inventories)**.
5. Always re-verify with `npx tsc -b --noEmit` + `npm run build` before declaring done.

*This document, the PDF, and the source ZIP together constitute a complete snapshot of the project as of
31 May 2026. Everything was built from scratch in one Claude Code session.*
