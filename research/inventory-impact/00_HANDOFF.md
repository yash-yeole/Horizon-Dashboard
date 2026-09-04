# HANDOFF — EIA Crude Inventory → Brent Impact Framework

**Session date:** 2026-06-23 · **Status:** ✅ complete (framework + validation built). Re-run live before the **24-Jun 10:30 ET** print.
**Read this top-to-bottom and you can resume cold.** All work lives in `rough_work/`.

---

## 0. TL;DR

We built a framework to assess how tomorrow's **weekly EIA crude inventory release** will move **Brent**. It's an **event study**, not a fair-value model: dependent variable is Brent's *reaction* to the print.

**Headline result: the inventory print is NOT a reliable Brent driver in the current (war-premium) regime → call is NEUTRAL.** The market-controlled inventory beta is the right sign but statistically insignificant in-sample, and has **negative out-of-sample skill** (validated 3 ways). Brent's ~35% round-trip on the geopolitical premium ($80→$118→$77) swamps a ±1% inventory effect.

---

## 1. The task (original ask)

Analyse one inventory series (chose **crude → Brent**) and build a framework to assess the likely market impact of the release. Focus: historical releases & reactions; when inventories mattered vs didn't; seasonal/regime effects; other amplifying/offsetting drivers.

**Deliverables:** (1) bull/bear/neutral expectation; (2) products/spreads most affected; (3) top-3 factors; (4) brief framework explanation.

---

## 2. Scope decisions (LOCKED — do not silently change)

- **Window = March 2026 → now only** (~16 weekly releases). User *explicitly refused* using the full 5-yr LCO history — wants only the current "war regime" because reactions are regime-dependent. This caps N≈16 (the binding statistical constraint; we designed around it).
- **Free / keyless sources only.** No Bloomberg/Reuters/TradingEconomics (all paid; TE guest tier is dead). The only key used is the **EIA** key the user already has in `backend/.env`.
- Deliverable form: **reusable notebooks** (in `rough_work/`), executed with outputs embedded.

---

## 3. Environment (IMPORTANT — desk was just changed)

- **Research venv (outside OneDrive, to dodge the dehydration bug):** `C:\Users\yash.yeole\.venvs\energy`
  - Interpreter: `C:\Users\yash.yeole\.venvs\energy\Scripts\python.exe`
  - System Python is now **3.13.7** (`C:\Program Files\Python313`); was 3.14.6 on the old desk.
  - Stack: pandas 3.0.3, numpy 2.5, scipy, pyarrow, httpx, requests, bs4, lxml, **yfinance 1.4.1, statsmodels 0.14.6**, scikit-learn, matplotlib, jupyterlab, ipykernel, dotenv. Frozen in `rough_work/requirements-research.txt` (122 pkgs).
- **Jupyter kernel:** registered as `energy`, display name **"Python (energy)"**. 
  - ⚠️ **Common gotcha:** `ModuleNotFoundError: No module named 'numpy'` in the notebook = wrong kernel selected. Fix: top-right kernel picker → **"Python (energy)"**. (A stray `horizon-rebuild` kernel exists and lacks our packages — don't use it.)
- **`.vscode/settings.json`** points the editor at the energy venv (fixes Pylance squiggles). Switch interpreter back to `backend/.venv` when editing the FastAPI backend (it needs fastapi/torch which the energy venv lacks).
- **No Jupyter CLI run-loop needed:** notebooks are generated + executed headless by the `_build_*.py` scripts via `nbclient` (kernel `energy`). To regenerate any notebook: run its builder with the venv python.

**Rebuild venv if on a new device:**
```bash
"C:/Program Files/Python313/python.exe" -m venv "C:/Users/<user>/.venvs/energy"
"C:/Users/<user>/.venvs/energy/Scripts/python.exe" -m pip install -r rough_work/requirements-research.txt
"C:/Users/<user>/.venvs/energy/Scripts/python.exe" -m ipykernel install --user --name energy --display-name "Python (energy)"
```

---

## 4. Data sources & plumbing (all free)

### 4a. Consensus / surprise
- **Investing.com** economic-calendar pages embed full `actual/forecast/previous` history in `<script id="__NEXT_DATA__">` JSON. Keyless. Parse: `data["props"]["pageProps"]["state"]["economicCalendarEventStore"]["occurrences"]`.
  - **Event 75 = EIA Crude Oil Inventories** ✅ (history back to 2024-07; this is the spine).
  - Event **959 = a MONTHLY series, NOT weekly gasoline** — do not use it for weekly gasoline.
  - Event **829 = Cushing**.
  - **Weekly gasoline/distillate event IDs were NOT found** (Investing soft-redirects bad IDs to 200; the search endpoint is gated). → OPEN ITEM. We sidestepped it (see 4c).
  - `occurrence_time` is the **exact UTC release time incl. DST + holiday shifts** (e.g. Mar=15:30Z EST, Apr+=14:30Z EDT, 28-May=16:00Z Memorial-Day delay). Key all reaction windows off this.
- **ForexFactory** weekly JSON `https://nfs.faireconomy.media/ff_calendar_thisweek.json` — upcoming consensus (crude only). Keyless. **Tomorrow's (24-Jun) consensus = −5.1 M bbl, previous −8.3.**
- `surprise = actual − forecast`. **Sign convention: positive surprise = bigger build than expected = BEARISH.**

### 4b. Actuals (validation + the level)
- **EIA API** (`api.eia.gov/v2/seriesid/{id}`, key in `backend/.env` as `HORIZON_EIA_API_KEY`). Series: `PET.WCESTUS1.W` crude, `PET.WGTSTUS1.W` gasoline, `PET.WDISTUS1.W` distillate. Levels in **k bbl** → ÷1000 for M bbl; W/W change via `.diff()`.
- **Validated: Investing `actual` == EIA W/W change, 16/16 exact.** Mapping: release Wednesday ↔ EIA week-ending **Friday ~5 days earlier**.

### 4c. Product surprise (gasoline/distillate)
- Weekly product consensus isn't reliably free → **use EIA actual W/W change** for gasoline/distillate (authoritative), with recent-trend as "expected" if a true surprise is needed. Cross-product spillover (your idea) enters this way.

### 4d. Price / reaction (Brent + spreads)
- **`Regime/data/*.csv`** = 1-min full forward curves, 2021→May-2026, weighted-mid per contract. Header: line 1 is `#meta…` comment, line 2 is real header `timestamp,c1||contract,c1||weighted_mid,c2||…`. Read with `pd.read_csv(comment="#", usecols=[…], dtype=str)`; timestamps are UTC `+00:00` (lexicographic sort == chronological).
  - `LCO_data.csv` = **ICE Brent** (front `c1` = our Brent price). Ends **2026-05-22 09:59Z**.
  - `CL_data.csv` = WTI. Ends 2026-05-22 14:59Z.
  - `LGO_data.csv` = **ICE gas oil ($/tonne → ÷7.45 for $/bbl)**. Ends 2026-05-20 09:59Z.
  - `HO_data.csv` (heating oil), `wtcl_lco_outrights_1min.csv` (WTI-Brent spread) — available, not yet used.
- **Gap fill (after CSVs end → today):** **yfinance** `BZ=F` 15m (60-day max lookback covers it).
- **Macro daily:** yfinance `DX-Y.NYB` (DXY), `^GSPC` (S&P 500), `BZ=F` (Brent). 15m only goes back 60d; 1-h back 730d; daily unlimited.
- **Reaction windows:** Brent log-return over **[t0, t0+2h]** and **[t0, same-day UTC close]**, where t0 = `occurrence_time`. Price at t0 via `Series.asof(t0)`.

---

## 5. Methodology — two-stage event study

The N≈16 problem is the whole design driver.

1. **Stage 1 — market model on DAILY data (~78 obs):** `BrentRet = β0 + β_dxy·DXYRet + β_spx·SPXRet + ε`. DXY/S&P move daily so betas are well-identified on the larger daily sample.
2. **Stage 2 — abnormal return on RELEASE days (~16 obs):** `abnormal = ε` on the release day (the move the market doesn't explain). Regress abnormal on `crude_surp` (Model A) and on `crude_surp + gas_chg + dist_chg` (Model B). Scarce events spent only on the inventory coefficient. **Keep ≤2-3 regressors** (N=16).
3. **Regime/amplifier overlay:** term-structure (M1-M2 backwardation), realized vol, geopolitical/news state — to judge *when* the (weak) signal breaks through.
4. **Spread routing:** measure WTI-Brent and gas-oil-crack reactions directly on the 1-min tapes.

**Why abnormal return (not raw):** isolates the inventory-attributable move from market noise. **Do NOT extrapolate the Stage-2 intercept as a forecast** — it captured the falling-market drift (regime), not inventory. Only the slope (β × surprise) is the inventory component.

---

## 6. Files in `rough_work/`

| File | What |
|---|---|
| `00_HANDOFF.md` | this document |
| `01_inventory_event_study.ipynb` | **Step 0** — event table: consensus surprise + EIA cross-check + Brent reaction windows |
| `02_step1_macro_abnormal.ipynb` | **Step 1** — market model → abnormal return → inventory beta |
| `03_step2_regime_call.ipynb` | **Step 2** — spreads, regime split, the call + framework write-up |
| `04_validation.ipynb` | **Step 3** — out-of-sample validation (LOOCV / walk-forward / 70-30) |
| `05_step4_news_layer.ipynb` | **Step 4** — GDELT news-intensity regime layer (#1 split + interaction) |
| `06_step5_api_surprise.ipynb` | **Step 5** — API-refined surprise (EIA−API), the one OOS improvement; pooling null |
| `07_reasoning_layer.ipynb` | **Step 6** — reasoning layer: news-tone driver ranking (top-3), RSS headline narrative, theme→spread routing |
| `_build_*.py` | regenerators for each notebook (run with venv python; they execute headless via nbclient) |
| `cache/event_table.parquet` | the assembled dataset (17 rows: 16 priced + 1 pending) |
| `cache/lco_recent.parquet`, `lco_c1.parquet`, `cl_c1.parquet`, `lgo_c1.parquet` | cached 1-min slices (Feb-20 → May) so big CSVs aren't re-parsed |
| `cache/gdelt_oilvol_raw.json` | cached GDELT oil-news intensity (Mar→now); offline reruns, avoids the throttle |
| `cache/api_weekly_656.json` | cached Investing "API Weekly Crude Oil Stock" history (event 656) |
| `cache/gdelt_oiltone.json` | cached GDELT oil-news TONE (2024-06→now) — the news-sentiment factor |
| `cache/news_headlines_recent.json` | cached FinancialJuice+OilPrice RSS oil headlines (live narrative) |
| `requirements-research.txt` | frozen venv |

Also: memory files `research-venv.md`, `inventory-impact-framework.md`, `venv-onedrive-corruption.md` under the Claude project memory dir.

---

## 7. Key results (actual numbers)

**Stage 1 (market model, N=78, R²=0.279):** β_dxy = **+4.92 (p=0.007)**, β_spx = −1.18 (p=0.18).
→ *Unconventional, regime-specific:* Brent and the **dollar co-moved positively** (both bid as war hedges; the usual negative oil/USD link inverted). Market explains only 28%; the geopolitical premium survives into the abnormal return.

**Stage 2 (N=16):**
- Model A: `abnormal ~ surprise` → β = **−0.253 %/Mbbl (p=0.32)**, R²=0.065
- Model B: `+ gas + dist` → crude β = **−0.373 (p=0.14)**, gas_chg −1.169 (p=0.18, *bearish gasoline builds = your spillover*), dist +0.523 (p=0.51), R²=0.330 (adj 0.162)
- Intraday 2h ~ surprise → +0.023 (p=0.71), ~zero
→ Right sign, **not significant**.

**Spreads (1-min, 11-12 releases, |corr| with surprise):** WTI-Brent **0.29**, WTI 0.29, Brent 0.08, gas-oil crack 0.01 — all p>0.38. WTI-Brent is the *relative* standout (US-specific print) but **none reliable**.

**Regime:** backwardation steep & positive throughout (M1-M2 **+3.1…+8.3**) → single tight-market regime, no contango weeks to contrast. Vol split didn't reveal amplification (corr ALL −0.29, HIGH-vol −0.11, LOW-vol −0.06; tiny n).

**Current state:** Brent ~**$76.8**, 2026 peak $118.3 → **−35% off peak** (premium unwinding). Last 4 surprises avg **−3.37** (draws chronically beating consensus = bullish surprises), yet price fell — inventories overridden.

---

## 8. Deliverables (the answer)

1. **Bias: NEUTRAL.** Inventory is a secondary driver. Consensus −5.1 already expects a big draw, so only an *extreme* print clears the noise band. Inventory-driven scenarios (β_B × surprise; regime drift excluded):
   - actual −9 (big draw) → +1.5% · −7 → +0.7% · **−5.1 in-line → ~0%** · −3 → −0.8% · +1 build → −2.3%
   - **Asymmetric lean:** mild bullish *only* on a draw >~8 M bbl; a surprise build adds to bearish momentum.
2. **Products/spreads:** **WTI-Brent** most surprise-sensitive (US-specific) > flat Brent; gas-oil crack ~nil; none statistically reliable this regime.
3. **Top-3 factors:** (1) geopolitical risk-premium regime [dominant] · (2) surprise vs the elevated −5.1 consensus [asymmetric] · (3) USD co-move + steep backwardation [macro + tight-physical].
4. **Framework:** surprise (actual−free-consensus) → two-stage abnormal-return event study → regime/amplifier overlay → spread routing.

---

## 9. Validation (Step 3)

Three schemes on N=16, skill measured vs **predict-the-mean** baseline (skill-R²>0 = beats the mean):

| Scheme | train:test | skill-R² A | skill-R² B | hit A |
|---|---|---|---|---|
| LOOCV | 15:1 | −0.05 | −0.07 | 0.50 |
| Walk-forward | ≥8 expanding | −0.11 | −2.42 | 0.25 |
| Holdout 70/30 | 11:5 | −2.75 | −13.5 | 0.00 |

(ret_2h target: skill-R² −0.06…−0.17, hit ~0.40.)

**Interpretation:** every OOS skill-R² is **negative** → the surprise does *worse than guessing the mean* out-of-sample = **no predictive skill**. Hit-rate ≈ coin flip (and noisy at this n — 0.50±0.12 on 16, ±0.22 on 5, so don't over-read individual values). **Model B overfits** (in-sample R²=0.33 → OOS deeply negative = textbook small-N overfitting; why we kept it lean). **This validates the NEUTRAL call** — a rigorously established null, corroborated 4 ways (raw corr +0.12, insignificant beta, negative OOS skill, visible regime). Low R² is *expected* for returns; the bar is positive skill, which we don't have. **Fix is data (quieter regime, more releases), not model.**

---

## 10. Caveats & open items

- **N≈16, single war regime** by design — conclusions are regime-specific. The same framework on a quiet tape would likely show a significant, validated inventory beta.
- **Consensus = free-calendar proxy** for the true survey (Investing forecast). Validated against EIA actuals, not against the paid survey.
- **Distillate weekly Investing event ID still unknown** — products currently use EIA actuals. Finding the right gasoline/distillate weekly event IDs would let us compute true *product* surprises.
- Reaction windows are +2h / same-day close; intraday macro-adjustment over 2h is approximate.
- Stage-2 abnormal uses full-sample macro betas (minor leakage in the macro step; the surprise→abnormal regression is the validated part).

## 11. Sensible next steps
- **Live re-run before 10:30 ET 24-Jun:** open all notebooks with the `energy` kernel and Run-All (consensus/price/EIA refresh automatically). Plug the API number (Tue-night, from the news feed) as an extra read.
- Find weekly gasoline/distillate Investing event IDs → true product surprises.
- Optional: extend to a quieter pre-war sub-period (would break the March-only scope — ask user first) to demonstrate a significant inventory beta for contrast.
- Optional: add the WTI-Brent outright tape (`wtcl_lco_outrights_1min.csv`) and HO for a fuller spread panel.

## 12. How to resume (commands)
```bash
PY="C:/Users/<user>/.venvs/energy/Scripts/python.exe"
# regenerate + execute any step (writes the .ipynb with outputs):
"$PY" rough_work/_build_notebook.py     # Step 0
"$PY" rough_work/_build_step1.py        # Step 1
"$PY" rough_work/_build_step2.py        # Step 2
"$PY" rough_work/_build_validation.py   # Step 3
```
Or open the `.ipynb`s directly and select the **"Python (energy)"** kernel.

---

## 13. Step 4 addendum — GDELT news/geopolitical layer (added 2026-06-24)

**Why:** our market model (DXY/S&P) couldn't see the geopolitical premium that swamped the inventory signal. GDELT oil-news **intensity** gives an objective handle on it.

**Source & fetch gotchas (painful to discover — keep these):**
- GDELT DOC 2.0: `https://api.gdeltproject.org/api/v2/doc/doc`, `mode=TimelineVolRaw`, `format=json`, `startdatetime/enddatetime=YYYYMMDDHHMMSS`. Free, keyless.
- Query: **`theme:ECON_OILPRICE sourcelang:english` — NO parentheses** (GDELT: "Parentheses may only be used around OR'd statements").
- **A browser `User-Agent` header is required** — the default python UA gets 429'd hard.
- **Throttles aggressively:** needs ~**50–60s spacing** between calls to clear the 429 penalty box (not the advertised 1/5s). Fetch is **cached** in `cache/gdelt_oilvol_raw.json` so reruns are offline; to refresh, delete it and re-pull patiently.
- Intensity = `value`/`norm` (oil articles ÷ total coverage). History back to ~2017 (not needed for the March-only model).

**Validation (passed):** intensity vs Brent realized-vol **+0.70**; highest-intensity days = biggest move days (Apr-8 −14%, Mar-23 −12%); higher in the Apr run-up (~1601) than now (~984). Credible regime gauge. **Caveat: intensity = magnitude, not direction** → conditioning variable, not a directional control.

**Result — HONEST NULL (conditioning did not rescue the signal):**
- Regime split (N=15, pre-release 5d backdrop, median): QUIET-news inv-beta **−0.09 (p=0.88)**, LOUD-news **−0.29 (p=0.67)**; interaction `surp×intensity` **p=0.73**. Opposite of the "inventories bite on quiet tapes" hypothesis, and all noise.
- **Confound:** intensity declined ~monotonically (≈155→≈50), so "quiet" ≈ "recent" → split entangled with time, underpowered at ~7–8/bucket.
- **Call unchanged: NEUTRAL.** Current tape is quiet (~9th pct) but quiet weeks showed ~zero inventory sensitivity, so that doesn't argue for trusting the print more.

**GDELT's real value:** (a) a *validated, reusable* geopolitical-regime gauge for the dashboard; (b) confirms factor #1's dominance — it did NOT surface a hidden inventory edge (consistent with the Step-3 OOS null).

**Snapshot:** pre-Step-4 restore point at `Documents/inventory_framework_snapshot_2026-06-24.zip` (unzip over `rough_work/`).

**Parked (long-term):** full GDELT **headline-impact engine** — 2017+ history, factor classification (LLM), scheduled-event (`expected/surprise/time-to-event`) tagging — a reusable dashboard capability, its own initiative. This is the user's "original idea (#3)"; it legitimately uses full history (unlike the March-only inventory model).

---

## 14. Step 5 addendum — API-refined surprise (added 2026-06-24) — the ONE real win

**Insight (user's):** by Wed 10:30 ET the market has already seen **API** (Tue 4:30pm ET) and repriced, so the genuinely new info in the EIA print is **`EIA − API`**, not `EIA − consensus` (stale). We'd been measuring against the wrong baseline.

**Data:** Investing.com event **656** = "API Weekly Crude Oil Stock" (free/keyless; found via the calendar AJAX service `/economic-calendar/Service/getCalendarFilteredData`, POST country[]=5). Tuesday ~20:30Z, ±M bbl, same sign convention as EIA. Cached `cache/api_weekly_656.json`. Map API→EIA: latest API within 2 days before the EIA release.

**Result — first positive OOS skill in the project:** on the clean intraday `ret_2h` window (API already priced by 10:30), `EIA−API` gives **R²=0.12, p=0.18, OOS=+0.04** vs consensus `R²=0.01, OOS=−0.17`. It *subsumes* the consensus surprise (which collapses to ~0 when both are included). Coherence check passes: `EIA−API` helps on intraday but *hurts* on daily abnormal (which double-counts the Tue-night API move) — exactly as theory predicts.

**Honest brakes:** still **not significant** (p=0.18), N=16, OOS only +0.04, and the **beta sign is counterintuitive (+) and unstable** → informative, not yet tradeable. Call stays **NEUTRAL**.

**Pooling null:** treating API as its own event (its own surprise + Tue +2h reaction) → ~30 events did NOT break the N wall: EIA beta (+) and API beta (−) have **opposite, insignificant signs**, so pooling cancels them. (Also API's +2h window truncates at the ~22:00Z ICE close → thin/small-variance reactions.) More data didn't help because the signal is genuinely weak in this regime.

**Tomorrow (24-Jun):** consensus −5.1 vs API −0.77 → **expectations unanchored**. Market likely sits near API's small draw, so a *solid* EIA draw (−5 to −7) that looks "in-line" vs the stale consensus would be an **upside surprise vs what's now priced.**

**Best current spec:** `ret_2h ≈ α + β·(EIA − API)` (β≈+0.08, R²0.12) — the keeper inventory variable, though still sub-significant.

**Snapshots:** `Documents/inventory_framework_snapshot_2026-06-24_pre-api-pool.zip` (pre-Step-5 rollback).

---

## 15. Step 6 — news-sentiment factor + reasoning layer (added 2026-06-24)

**News tone IS a significant factor** (user insisted, correctly). GDELT `TimelineTone` (theme:ECON_OILPRICE), cached `cache/gdelt_oiltone.json` (2024-06→now). Added **Δtone** (change in oil-news tone) to Stage 1 (war regime): **R² 0.279→0.344, Δtone β=−0.027, p=0.00** (worsening tone → supply-scare → Brent up). It belongs in Stage 1 (daily, high-N) — no overfit, sidesteps the N=16 wall (that only ever bound the 16-event inventory term).

**Three things the data settled:**
- **NOT stationary** — tone β ≈ 0 pre-war (p=0.92), strong in-war (p=0.00). So "train news beta on full history" *backfires* (dilutes the war effect); estimate on the war window only. (The tone *score* is stationary; the price *response* to it is not.)
- **Contemporaneous, not predictive** — lagged tone p=0.96. Explains moves, doesn't forecast them. So news can't predict the inventory print; it's for *attribution/context*.
- **Doesn't rescue inventory** — tone-cleaning the abnormal left the inventory beta unchanged (R² 0.022→0.024). Inventories are orthogonal to news, genuinely absent — not hidden behind it.

**Reasoning layer (`07_reasoning_layer.ipynb`):** for the *deliverables* (not the bull/bear prediction):
- **Top-3 driver ranking** (standardized β, war regime): **1) DXY +0.38 (p=.003), 2) News Δtone −0.28 (p<.001), 3) S&P −0.15 (ns)**. Inventory ranks below all (event-level, insignificant). DXY+news = the one geopolitical regime, two ways.
- **Headline narrative** from RSS (FinancialJuice/OilPrice, `cache/news_headlines_recent.json`): current tape = **Hormuz de-escalation** (US-Iran hotline, Iranian oil returning) + **political pressure for lower prices** (Trump/DOJ) → premium *unwinding* (bearish backdrop, Brent ~$76 −35% off peak).
- **Theme→spread routing**: keyword-tally of headlines → crude/geopolitical dominates (6 vs gasoline 2 vs distillate 0) → focus on **flat Brent + WTI-Brent**, not product cracks.

**GDELT throttle note:** heavy this session — ArtList 429'd repeatedly even at 60-75s spacing. Used **RSS feeds instead for headlines** (keyless, no throttle) — the better live-narrative source anyway.

---

## 16. Dashboard integration — "Release Impact" feature (added 2026-06-24)

**Status: code-complete + endpoint verified end-to-end.** Productionizes the framework into a live dashboard feature.

**Files added/edited (all in the tracked repo, not rough_work):**
- Backend: `backend/app/models.py` (+ReleaseImpactResponse/ReleaseScenario/DriverFactor/NewsTheme), `backend/app/services/release_impact.py` (new — `assess()`), `backend/app/routers/release_impact.py` (new — `GET /api/release-impact`), `backend/app/main.py` (registered router), `backend/data/release_impact_cache.json` (seeded last-good API value).
- Frontend: `energy-dashboard/src/types/api.ts` (+types), `src/services/api.ts` (`api.releaseImpact()`), `src/hooks/useReleaseImpact.ts` (new), `src/components/widgets/ReleaseImpact.tsx` (new — `ReleaseImpactCard` + `ReleaseImpactSection`), wired into `src/pages/Dashboard.tsx` (compact card → `/inventories#release-impact`) and `src/pages/Inventories.tsx` (full expandable section pinned at top).

**Endpoint logic:** live consensus (**ForexFactory primary**, Investing fallback) + API number (Investing event 656, **persisted to `data/release_impact_cache.json`** so a 403 still serves last-good) + surprise scenarios (qualitative `lean`, NOT a fake-precise % — the β is sign-unstable) + news theme tally/spread routing + headlines (RSS) over a **versioned model snapshot** (inventory β, top-3 driver ranking, framework). 15-min TTL cache; serves stale on failure. **NOTE: Investing 403's under heavy use (rate-limit) — FF + the API cache keep it populated.**

**How to RUN locally (⚠️ `backend/.venv` is OneDrive-dehydrated again — pydantic_core missing):**
- Verified with the research venv + FinBERT off (torch import is lazy, so the app boots without it):
  ```bash
  PY="C:/Users/<user>/.venvs/energy/Scripts/python.exe"
  "$PY" -m pip install "uvicorn[standard]" openpyxl websockets   # one-time: add to energy venv
  cd backend && HORIZON_FINBERT_ENABLED=false PYTHONPATH=. "$PY" -m uvicorn app.main:app --port 8000
  # GET http://127.0.0.1:8000/api/release-impact  -> verified 200, full payload
  ```
- For a *real* backend run (with FinBERT), rehydrate `backend/.venv` (recreate + `pip install -r requirements.txt` + `attrib +P` to pin) OR build a venv outside OneDrive. The Docker deploy is unaffected (torch installed in the image).
- Frontend: `cd energy-dashboard && npm run dev` (Vite proxies `/api` → :8000). `npx tsc --noEmit` = **0 errors**.

**Verified:** endpoint returns consensus −3.9 (FF), API −0.765 (cache), gap −3.13, scenarios w/ correct leans (draws→bullish, build→bearish), top-3 factors, news themes (Crude/geopolitics 10 → spread "flat Brent + WTI-Brent"), 6 live headlines. Frontend typechecks clean.

**DEPLOY architecture (HF Spaces — two separate Spaces):**
- **Backend** = HF **Docker** Space `yashyeole-horizon-backend` → `https://yashyeole-horizon-backend.hf.space` (frontmatter in `backend/README.md`; `backend/Dockerfile` installs CPU torch + prebakes FinBERT; runs uvicorn on 7860).
- **Frontend** = a **separate** HF Space (name NOT in repo) — built with `energy-dashboard/.env.production` `VITE_API_BASE_URL=https://yashyeole-horizon-backend.hf.space`, deployed as static.
- **Git remote here is GitHub** (`yash0x-repo/energy-dashboard`); the HF Spaces have their own remotes (`https://huggingface.co/spaces/...`) not configured in this clone.

**TO DEPLOY (pending — needs user input):** (1) commit the changes; (2) push the **backend** subtree to the backend HF Space remote → triggers Docker rebuild; (3) `npm run build` the **frontend** and push to the **frontend** HF Space remote. **BLOCKED on:** the *frontend* HF Space name + an HF auth token (none in repo). Backend Space is known (`yashyeole-horizon-backend`) but still needs the token to push.
