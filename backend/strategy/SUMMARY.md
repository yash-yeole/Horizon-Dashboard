# Strategy Engine — Paper-Trading / Backtest / Live (Phase 7)

Extends the historical regime + fair-value framework (`../model`, Phases 1–6) into a
paper-trading and live-analysis engine. Everything here is segregated in `strategy/`.

_Last updated: 2026-06-15_

---

## Goal

Use the **trained** regime + fair-value model to score live/intraday market data,
turn deviations-from-fair-value into trade decisions, run a full backtest with a
complete trade/signal audit trail, and run the **same engine** live so the dashboard
can become a real-time paper-trading platform.

## Locked decisions (agreed with user)

| Decision | Choice |
|---|---|
| How to use the DB data | **Score with the trained Phase 1–6 model — no re-fit** |
| First structure | **WTI c1-c2 calendar spread** |
| Decision cadence | **Intraday 15-min** (regime + fair value classified **daily**, held constant within the day; only the live spread / z vary intraday) |
| Dashboard | Integrate **after** successful testing |
| Costs / slippage | Parameterized, **default 0** |

---

## Data source

`strategy/files/bars_15min_YYYYMMDD.db` — SQLite, **one DB per trading day**, written
live by an upstream collector (WAL mode).

- Tables `{PRODUCT}_{TENOR}`: `CL`=WTI (CME), `CO`=Brent (ICE). 15-min OHLCV, UTC bar-open.
- Current file `bars_15min_20260612.db` covers **2026-06-12 → 06-15** (06-13 Sat skipped),
  ~79 bars/contract, tenors N26..Z27.
- **WAL/SHM checked:** read-only connection reads through the `-wal` correctly (ro and rw
  return identical rows). A live writer is attached (observed WAL checkpoint + shm touch),
  but bars can stall during quiet/closed windows. The `-wal`/`-shm` files vanishing is
  **normal**: SQLite checkpoints + deletes them when the last connection closes; OneDrive
  then propagates the deletion. Their absence means data is safely in the main `.db`.
- **Configurable data path** (`data_feed.py`): defaults to the local OneDrive copy, but
  `set_data_dir(path)`, `use_live_source()`, or env var `REGIME_DATA_DIR` can point it at
  the live source drive `I:\Public\Siddharth Raj\lightstreamer_data` (per files/README.md).
- **WAL safety guard** (`_connect`): if a snapshot has a `-wal` but no `-shm` (partial
  OneDrive copy mid-write), opens read-write so SQLite rebuilds `-shm` and recovers the WAL
  rows; otherwise stays strictly read-only so the live writer is never blocked.
- **Confirmed live source: `I:\Public\Summer Interns Energy\DB`** — reachable, 144 bars
  (CL_N26) vs 83 on the OneDrive copy; data to `2026-06-15 23:45`. This is now the
  **automatic default** (falls back to `strategy/files/` if the drive is unreachable).
  Connection uses `immutable=1` (SMB/network paths can't do WAL shared-memory locking);
  WAL rows in-flight are skipped but the committed main .db gives ~16h more data than OneDrive.
  The `_connect()` fallback chain: (1) read-only → (2) rw WAL recovery → (3) immutable=1.
- **Caveat:** only CL+CO, ~3 days so far. This is the **go-forward live feed**, *not* a long
  backtest history. The backtest becomes meaningful as more daily DB files accumulate.

---

## Modules (all in `strategy/`, validated)

| File | Role |
|---|---|
| `data_feed.py` | Read DB bars (read-only, WAL-safe). `BacktestFeed` iterates history; `LiveFeed.poll()` returns new bars from the appended file. Front-tenor roll map → c1-c2 spread. CL c1-c2 = N26-Q26. **Same `Bar` interface for backtest and live.** |
| `fair_value.py` | Bridge to `../model/pipeline.py`. Builds daily rows for the DB days from the 15-min bars, appends to `pipeline.daily_panel`, fetches fundamentals, runs `score_regimes` + `fit_fairvalue`. Trains on `split=="train"` (pre-2026-03-01) and scores DB days **forward** → daily regime + fair_value + resid_std. |
| `strategy.py` | `CalendarMeanReversion`. `z = (spread − fair_value) / resid_std`. SHORT if z>0 (rich) / BUY if z<0 (cheap). Entry \|z\|≥2, exit \|z\|≤0.5, stop \|z\|≥3. OOD or \|z\|≥4 → NO_TRADE dislocation guard; LOW-confidence suppressed. target = fair value, stop = fair ± 3·resid_std. |
| `trade_log.py` | `SignalLog` = **every** opportunity (ts, regime, instrument, action, z, rationale, confidence). `TradeLog` = full lifecycle: planned/actual entry+exit, target, stop, gross/net PnL, costs, slippage, equity contribution, win flag, hold time. |
| `metrics.py` | win/loss, win rate, profit factor, max drawdown, Sharpe, exit-reason counts, per-regime breakdown. |
| `backtest.py` | `Engine.step(bar)` event loop = **one engine for backtest (iterate) and live (poll)**. `EngineConfig` for product/size/costs. |
| `20_backtest.ipynb` | Runs WTI c1-c2 end-to-end; shows feed, daily fair value, signals, trades, equity, stats; saves to `strategy/cache/`. |

Outputs: `strategy/cache/` → `bt_signals.parquet`, `bt_daymap.parquet`, `bt_summary.json`
(+ `bt_trades.parquet` when trades exist). `cache/` is gitignored.

---

## Results (current 3-day DB)

- All DB days score as regime **M\|H\|Back**, fair value ≈ **0.97–1.02**, resid_std ≈ **0.666**.
- Actual spread ≈ **1.14–1.67** → intraday **z range 0.25–0.98** (mildly rich, **not** OOD).
- Under locked thresholds: **0 trades / 80 NO_TRADE** — correct. Max \|z\| = 0.98 never reached
  the entry threshold of 2.0 (a quiet, in-distribution window should not trade noise).
- **Lifecycle/PnL validated** by lowering thresholds: a SHORT entered @1.56, exited @1.33
  (TARGET), net **+0.23** — correct sign and math.
- Note: lowering entry to 1.5 would still give 0 trades on this data (max \|z\| = 0.98);
  trades require either more volatile days from new DB files or a much lower threshold.

---

## What's next

1. Accumulate more daily DB files → a real backtest history with actual trades.
2. Background feed-watcher to confirm/consume live updates as they arrive.
3. Wire the engine into the dashboard (live view) as a real-time paper-trading platform.
4. Optionally extend to Brent calendar and WTI-Brent once more data is available.
