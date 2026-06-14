# HORIZON Energy Terminal — Project Checklist

_Last updated: 2026-06-11_

Tracks which dashboard features are wired to **live data** vs still **static/mock**,
and what's left to do. "Free" = no paid data feed required; "Paid" = needs a
commercial data subscription.

---

## ✅ Done

### Infrastructure / backend
- [x] FastAPI backend proxy with in-memory TTL cache + graceful stale fallback
- [x] Live quotes via Yahoo Finance (no key): Brent, WTI, RBOB, Heating Oil, VIX, DXY, S&P 500, US 10Y, Gold, Copper
- [x] History endpoint (`/api/history`) — daily/intraday series
- [x] Forward curves for all 5 commodities: **Brent + Gas Oil** (ICE settlement CSV), **WTI/Heating Oil/RBOB** (assembled from Yahoo monthly futures contracts). Selectable curve card on Dashboard, Crude, Products pages. _(Gas Oil needs its ICE CSV dropped in — graceful "unavailable" until then.)_
- [x] **Calendar spread + butterfly history** (`/api/curve/{id}/structure`) — M1-M2, M1-M6, M1-M12 spreads and 1-2-3, 2-3-4, 4-5-6 butterflies for all 5 commodities. Brent/GasOil from CSV; WTI/HO/RBOB from Yahoo contract months.
- [x] EIA Open Data integration (key in git-ignored `backend/.env`)
- [x] CFTC Commitments of Traders — free Socrata API (no token)
- [x] Baker Hughes rig count — official Excel files (NA weekly + Intl monthly)
- [x] **News pipeline** — merged FinancialJuice + OilPrice RSS, energy-filtered, deduped by `event_key`
- [x] **Groq LLM sentiment scorer** (LLaMA 3.3-70B, free tier) — directional crude-price impact scoring; Gemini fallback; lexicon offline fallback
- [x] **Persistent news store** — 40-item sliding queue in `.news_store.json` (gitignored); score-only-new architecture (zero LLM calls on cache hits); survives restarts; offline fallback to stored feed
- [x] **Energy calendar endpoint** (`/api/calendar`) — rule-based, no API key: EIA Petroleum (Wed 10:30 ET + 2026 holiday exceptions), EIA Nat Gas (Thu 10:30 ET), Baker Hughes (Fri 13:00 ET), CFTC COT (exact 2026 dates), OPEC+ ministerial + IEA OMR + OPEC MOMR + EIA STEO (monthly, hard-coded 2026)
- [x] AIS tanker WebSocket consumer (aisstream.io) — vessels, chokepoints, heatmap

### Live data wired into the UI
- [x] Hero tiles + ticker tape (Dashboard) — live quotes
- [x] **Dubai Crude** — synthetic proxy (Brent − $2.00 EFS), labeled "Indicative"
- [x] Live price chart — 6 symbols including Dubai, up to 1Y history, candlestick + area
- [x] **Forward Curve card** — selectable (Brent/WTI/RBOB/HO/GasOil), backwardation/contango, Dashboard + Crude + Products tabs
- [x] **StructureCurveCard** — calendar spreads (M1-M2/M1-M6/M1-M12) and butterflies (1-2-3/2-3-4/4-5-6), commodity dropdown, on Dashboard + Crude tab
- [x] **News feed** — live RSS, AI-scored sentiment, 40-item memory queue
- [x] **Sentiment gauge** — embedded inside the Breaking News box (recency-decayed, confidence-weighted, crude-only); 5-tier labels (StronglyBullish → StronglyBearish)
- [x] **EIA Inventories page** — crude, Cushing, gasoline, distillate, propane, SPR, refinery utilization, production, imports/exports, days-of-supply
- [x] **CFTC COT positioning** — WTI + Brent managed-money net positions, weekly history on Crude page
- [x] **Rig count** — Baker Hughes NA weekly + Intl monthly, compact widget on Dashboard
- [x] Correlation matrix (Dashboard + Macro) — real 30d rolling daily-return correlations
- [x] Comparison / rebased charts, volatility panel, lead-lag analysis (Analytics)
- [x] **Z-score engine** — 16 metrics, robust MAD estimator, Tier A (% moves, spreads, positioning) + Tier B (price stretch, inventory w/w), hysteresis (±0.3σ buffer to prevent flapping). `lib/zscore.ts` + `lib/zmetrics.ts` built and verified.
- [x] **AlertsProvider + AlertToasts** — client-side edge-triggered alert engine, rules in localStorage, toasts + bell badge + Alerts page
- [x] **Live Economic Calendar** — EconomicCalendar widget rewritten to use `/api/calendar`; grouped by date (Today/Tomorrow/date), color-coded by source (cyan=EIA, purple=CFTC, amber=OPEC, blue=IEA, green=BH), holiday-delay flag
- [x] **Topbar redesign** — removed search/ICE/NYMEX/CME status; PageHeader title+actions portalled in via `createPortal`; horizontal alerts bar
- [x] **ImpactBadge, ThemeBadge, KindBadge** UI components; NewsModal with sentiment details
- [x] **MarketMovers** moved to Analytics tab (removed from Dashboard)
- [x] **ShippingCongestion** stays on Freight tab (removed from Dashboard)
- [x] **WeatherRiskPanel** stays on Weather tab (removed from Dashboard)
- [x] **Dashboard cleanup** — now 5 clean sections: alerts bar → metric tiles → price chart + news → term structure row (curves + spreads + flys) → correlation/rig count → cross-commodity/calendar
- [x] Tanker map (AIS Phase 1) — MapLibre, heatmap, clustered markers, chokepoint counts

---

## ⬜ To Do — Free (no paid feed)

### Alerts
- [ ] **Wire z-score metrics into AlertsProvider** — `buildZMetrics()` exists in `lib/zmetrics.ts` but is not yet called inside `AlertsProvider`. Needs: fetch 4×1Y price history + CFTC + EIA in provider; call `buildZMetrics()`; track prev tier per metric; fire Watch/Elevated/High `FiredAlert` on tier escalation; expose `zMetrics` via context
- [ ] **Alerts.tsx — "Statistical Anomaly Monitor" section** — display the 16 z-score metrics with current tier badges, z values, and sparkline. Group by Tier A / Tier B.
- [ ] Phase 2: server-side alert engine + external delivery (email / Telegram / Discord)

### Data / Features
- [ ] **PADD-level regional stocks** — replace static regional map on Inventories page (EIA key already configured)
- [ ] **Macro tiles** EUR/USD + US CPI — currently static (need a free FX/macro source, e.g. Open Exchange Rates free tier or Frankfurter API for EUR/USD)
- [ ] **Weather page** — connect Open-Meteo (free, no key) for real temps, HDD/CDD, anomalies
- [ ] **Gas Oil forward curve** — drop `GasOilSettle.csv` into project root to light up Gas Oil spreads/flys (currently returns 503 gracefully)

### Shipping Phase 2
- [ ] 7d/30d chokepoint history (needs persistence layer)
- [ ] Floating-storage detection (vessels stationary > 24h)
- [ ] Route-level vessel density (AG→China etc.)

---

## ⬜ To Do — Paid / Blocked

- [ ] **Freight / Baltic tanker rates** (Freight page)
- [ ] Remaining spreads: **Gasoil-Brent, WTI-Dubai, Gas Oil-Heat** (need ICE Gas Oil / Dubai feeds)

---

## 🔧 Polish / Engineering

- [ ] Market Movers shows raw Yahoo tickers (e.g. `CL=F`) — prettify symbols
- [ ] Code-split bundle (Vite warns: chunks > 500 kB)
- [ ] Non-functional placeholder buttons (Layout, Export, Add to watchlist, Save)
- [ ] Production deploy config (`VITE_API_BASE_URL`, CORS origins, process manager)
- [ ] Automated tests (backend + frontend)

---

## 📡 Data Sources & Keys

| Source | Powers | Auth |
|---|---|---|
| **Yahoo Finance** (`query1.finance.yahoo.com`) | Live quotes, history, sparklines, forward curve contract months | None |
| **EIA Open Data v2** (`api.eia.gov/v2`) | Inventories, imports/exports, utilization, production | Free key — `HORIZON_EIA_API_KEY` in `.env` |
| **FinancialJuice RSS** | News feed — breaking energy squawks | None (public RSS) |
| **OilPrice.com RSS** | News feed — energy articles with summaries | None (public RSS) |
| **Groq API** (`api.groq.com/openai/v1`) | LLM sentiment scoring (LLaMA 3.3-70B) | Free key — `HORIZON_GROQ_API_KEY` in `.env` |
| **Google Gemini** (`generativelanguage.googleapis.com`) | LLM sentiment fallback | Free key — `HORIZON_GEMINI_API_KEY` in `.env` (optional) |
| **CFTC Socrata** (`publicreporting.cftc.gov`) | COT positioning — WTI, Brent, RBOB, Heating Oil | None |
| **Baker Hughes** (`rigcount.bakerhughes.com`) | NA weekly + Intl monthly rig count | None (free, attribution required) |
| **aisstream.io** (WebSocket) | Live AIS vessel positions, tanker map, chokepoints | Free key — `HORIZON_AISSTREAM_API_KEY` in `.env` |
| **ICE Settlement CSV** (`LCOSettle_2(in).csv`) | Brent forward curve + spread/fly history | Local file, shipped with repo |
| **CFTC Release Schedule** | 2026 COT release dates (holiday-adjusted) | Hard-coded (one-time scrape) |
| **EIA Release Schedule** | 2026 Petroleum report holiday exceptions | Hard-coded (one-time scrape) |

_Secrets live in `backend/.env` — gitignored. Never commit._
