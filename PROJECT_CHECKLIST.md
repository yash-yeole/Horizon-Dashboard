# HORIZON Energy Terminal — Project Checklist

_Last updated: 2026-06-02_

Tracks which dashboard features are wired to **live data** vs still **static/mock**,
and what's left to do. "Free" = no paid data feed required; "Paid" = needs a
commercial data subscription.

---

## ✅ Done

### Infrastructure / backend
- [x] FastAPI backend proxy with in-memory TTL cache + graceful stale fallback
- [x] Live quotes via Yahoo Finance (no key): Brent, WTI, RBOB, Heating Oil, VIX, DXY, S&P 500, US 10Y, Gold, Copper
- [x] History endpoint (`/api/history`) — daily/intraday series
- [x] Forward curve endpoint (`/api/curve`) from settlement CSV
- [x] EIA Open Data integration (key stored in git-ignored `backend/.env`)

### Live data wired into the UI
- [x] Hero tiles + ticker tape (Dashboard) — live quotes
- [x] Macro page tiles + indicators (10Y, Gold, Copper, S&P, VIX, DXY) — live
- [x] Crude page grades/benchmarks board — live (where Yahoo provides)
- [x] Products page benchmarks board — live
- [x] Live price charts + cross-commodity rebasing
- [x] **EIA Inventories page** — crude, Cushing, gasoline, distillate, propane, SPR, refinery utilization, production
- [x] **EIA trade & demand** — crude imports/exports, net imports, gasoline/distillate demand, days-of-supply (computed)
- [x] **Rig count (EIA)** — Baker Hughes US rotary rigs via EIA (monthly), chart + stat card
- [x] **Rig count (Baker Hughes, full)** — official BH Excel files (free, with attribution): NA **weekly** (US/Canada totals, oil-vs-gas, trajectory, 14 basins, land/offshore) + International **monthly** (by region, worldwide total, 24-mo history). Page-scrape → download → parse (openpyxl) → persist + Refresh. Full section on Inventories + compact widget on Dashboard.
- [x] EIA: fetch-once + **persist to disk** + manual **Refresh button** (no auto-polling)
- [x] Dashboard "US Crude Inventories" chart — live EIA
- [x] **Crude spreads** (3 of 6): Brent-WTI, RBOB-Brent, 3:2:1 Crack — computed live
- [x] **Market Movers** — top gainers/losers derived live from quotes
- [x] **Correlation matrix** (Dashboard + Macro) — real daily-return correlations
- [x] **Comparison / rebased charts** (Macro, Products) — live histories
- [x] **Volatility panel** (Analytics) — realized vol from returns
- [x] **Analytics panels** (multiline, area, correlation, spreads) — live
- [x] Removed unused "Yahoo Live" status box from Dashboard
- [x] **News feed** — merged **FinancialJuice + OilPrice** RSS (free, no key), energy-keyword filtered, category tagging, deduped & sorted newest-first, modal with article links (Dashboard feed + News page). Resilient: if one feed is down/rate-limited, the other still serves.
  - [x] Sentiment: **interim keyword lexicon** (placeholder — works, but to be replaced)
- [x] **CFTC Commitments of Traders** — free Socrata API (no token); WTI, Brent (NYMEX Last Day), RBOB, Heating Oil positioning by trader class + weekly net-position history; "Trader Positioning" section on the Crude page

---

## ⬜ To Do — Free (no paid feed)

- [ ] **Weather page** via Open-Meteo (free, no key) — temps, HDD/CDD, anomalies _(user has a separate plan — later)_
- [ ] **News feed** ← _next up per plan_ (see Paid/Free note below)
- [ ] **More EIA datasets** (key already configured):
  - [x] ~~Days-of-supply, crude imports/exports~~ ✅ done
  - [x] ~~Rig count (Baker Hughes via EIA, monthly)~~ ✅ done
  - [ ] PADD-level regional stocks (replace the static regional map)
  - [ ] Natural-gas storage — _skipped (not needed)_
- [ ] **News sentiment — proper model** _(deferred, do later)_: replace the keyword lexicon with an ML classifier (e.g. FinBERT / a finance-tuned transformer, free & local) to label headlines bullish/bearish/neutral with real context understanding. Backend already has a clean `_classify()` seam to swap in.
- [ ] **Real alerts engine** — generate alerts from live thresholds (price moves, inventory draws) instead of static `ALERTS`
- [ ] **Macro tiles** EUR/USD + US CPI — currently static (need a free FX/macro source)
- [ ] **Economic calendar** — currently static (free sources exist but messy)

## ⬜ To Do — Paid / Blocked (needs subscription)

- [ ] **Freight / Baltic tanker rates** (Freight page)
- [ ] **Port congestion / storm tracking** (AIS / satellite)
- [ ] Remaining 3 spreads: **Gasoil-Brent, WTI-Dubai, Gas Oil-Heat** (need ICE Gas Oil / Dubai feeds)

---

## 🔧 Polish / Engineering (not data)

- [ ] Market Movers shows raw Yahoo tickers (e.g. `CL=F`) — prettify symbols
- [ ] Code-split bundle (Vite warns: chunks > 500 kB)
- [ ] Non-functional placeholder buttons (Layout, Export, Add to watchlist, Save)
- [ ] Production deploy config (`VITE_API_BASE_URL`, CORS origins, process manager)
- [ ] Automated tests (backend + frontend)

---

## 📡 Data Sources & Keys

| Source | Powers | API key |
|---|---|---|
| **Yahoo Finance** (`query1.finance.yahoo.com/v8`) | Quotes, charts, spreads, correlations, comparison, volatility, movers | None |
| **EIA Open Data** (`api.eia.gov/v2`) | Inventories page + Dashboard crude-stocks chart + rig count | Free — set in `backend/.env` |
| **FinancialJuice RSS** (`feed.ashx?xy=rss`) | News feed — squawk headlines (energy-filtered, locally sentiment-tagged) | None (public RSS) |
| **OilPrice RSS** (`oilprice.com/rss/main`) | News feed — energy articles with summaries | None (public RSS) |
| **CFTC COT** (`publicreporting.cftc.gov` Socrata) | Trader positioning on the Crude page | None (no token) |
| **Baker Hughes** (`rigcount.bakerhughes.com` Excel) | Rig count — NA weekly + International monthly (Inventories + Dashboard) | None (free, attribution required) |

_No new API keys are required for anything built so far._
