"""Step 0 - Event table + raw surprise/reaction correlation

Build + execute rough_work/01_inventory_event_study.ipynb (Step 0).
Run with the research venv python. Uses nbformat + nbclient (kernel 'energy').

Auto-extracted from _build_notebook.py (was a notebook); run with the energy venv.
"""

# # EIA Inventory → Brent Impact — **Step 0: Event-Study Dataset**
#
# Assembles one row per weekly **EIA crude release** (Mar 2026 → now) with the
# market **surprise** and Brent's **reaction**, so later steps can estimate how
# much a unit of inventory surprise moves Brent *after controlling for the market*.
#
# **Design (locked):** scope = March→now, **free sources only**.
# - **Surprise** = `actual − consensus`. Consensus from Investing.com (keyless); actual
#   cross-checked against the EIA print.
# - **Reaction** = Brent log-return over **[t0, t0+2h]** and **[t0, same-day close]**,
#   where `t0` is the exact release timestamp (UTC, incl. DST/holiday shifts).
# - **Price** = ICE Brent front (LCO `c1`, 1-min) to 22-May-2026, then yfinance `BZ=F` 15m for the gap.
# - **Products** (gasoline/distillate): actual W/W change from EIA (weekly product consensus
#   isn't reliably free); their *expected* is built in Step 1.
#
# Two-stage plan downstream: macro betas from daily data → **abnormal return** on releases →
# inventory betas. This notebook only builds the dataset.

# ## 0. Imports & config

import json, re, time, warnings
from pathlib import Path
import numpy as np, pandas as pd, httpx
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

ROOT    = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
LCO_CSV = ROOT / "Regime/data/LCO_data.csv"
CACHE   = ROOT / "research/inventory-impact/cache"; CACHE.mkdir(parents=True, exist_ok=True)
START   = "2026-02-20"                      # a little before March -> clean baseline
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

def eia_key():
    for ln in (ROOT/"backend/.env").read_text().splitlines():
        if ln.startswith("HORIZON_EIA_API_KEY="):
            return ln.split("=", 1)[1].strip()
EIA_KEY = eia_key()

pd.set_option("display.width", 200, "display.max_columns", 30,
              "display.float_format", lambda x: f"{x:,.3f}")
print("EIA key loaded:", bool(EIA_KEY))


# ## 1. Consensus history — Investing.com (free, keyless)
#
# Investing embeds full `actual / forecast / previous` history in the page JSON.
# Event **75 = EIA Crude Oil Inventories**. `surprise = actual − forecast`
# (**positive = bigger build than expected = bearish**).

def fetch_consensus(slug_id: str) -> pd.DataFrame:
    html = httpx.Client(timeout=25, follow_redirects=True).get(
        f"https://www.investing.com/economic-calendar/{slug_id}", headers=UA).text
    blob = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S).group(1)
    occ  = json.loads(blob)["props"]["pageProps"]["state"]["economicCalendarEventStore"]["occurrences"]
    df = pd.DataFrame([{"release": pd.to_datetime(o["occurrence_time"], utc=True),
                        "actual": o.get("actual"), "forecast": o.get("forecast"),
                        "previous": o.get("previous")} for o in occ])
    return df.dropna(subset=["release"]).sort_values("release").reset_index(drop=True)

crude = fetch_consensus("eia-crude-oil-inventories-75")
crude = crude[crude["release"] >= "2026-03-01"].reset_index(drop=True)
crude["surprise"] = crude["actual"] - crude["forecast"]
crude.tail(8)


# ## 2. EIA actuals — validate crude & pull product features
#
# Confirm Investing's `actual` **equals the EIA print** (data integrity), and pull
# gasoline/distillate W/W changes for the cross-product spillover. Each Wednesday
# release maps to the EIA week-ending **Friday ~5 days earlier**.

def eia_change(series_id: str, length: int = 40) -> pd.Series:
    d = httpx.Client(timeout=25).get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                                     params={"api_key": EIA_KEY, "length": length}).json()["response"]["data"]
    s = pd.DataFrame(d)[["period", "value"]]
    s["period"] = pd.to_datetime(s["period"]); s["value"] = pd.to_numeric(s["value"])
    s = s.sort_values("period")
    return s.assign(chg=s["value"].diff() / 1000.0).set_index("period")["chg"]   # k bbl -> M bbl

crude_chg = eia_change("PET.WCESTUS1.W")
gas_chg   = eia_change("PET.WGTSTUS1.W")
dist_chg  = eia_change("PET.WDISTUS1.W")

def eia_at_release(chg: pd.Series, release_utc) -> float:
    we = (release_utc.tz_convert(None) - pd.Timedelta(days=5)).normalize()
    i  = (chg.index - we).to_series().abs().values.argmin()
    return float(chg.iloc[i])

chk = crude.dropna(subset=["actual"]).copy()
chk["eia"]   = chk["release"].map(lambda r: eia_at_release(crude_chg, r))
chk["match"] = np.isclose(chk["actual"], chk["eia"], atol=0.01)
print(f"Investing actual == EIA change for {chk['match'].sum()}/{len(chk)} releases")
chk[["release", "actual", "eia", "match"]].tail(6)


# ## 3. Brent price series — LCO 1-min (to 22-May) + yfinance `BZ=F` 15m (gap)

def load_lco(start: str = START) -> pd.DataFrame:
    cache = CACHE / "lco_recent.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    cols = ["timestamp", "c1||contract", "c1||weighted_mid", "c2||weighted_mid"]
    raw = pd.read_csv(LCO_CSV, comment="#", usecols=cols, dtype=str)
    raw = raw[raw["timestamp"] >= start]                  # lexicographic == chrono (all +00:00)
    out = pd.DataFrame({"ts": pd.to_datetime(raw["timestamp"], utc=True),
                        "c1": raw["c1||contract"],
                        "c1_mid": pd.to_numeric(raw["c1||weighted_mid"], errors="coerce"),
                        "c2_mid": pd.to_numeric(raw["c2||weighted_mid"], errors="coerce")}
                       ).dropna(subset=["c1_mid"]).set_index("ts").sort_index()
    out.to_parquet(cache)
    return out

def load_yf_brent() -> pd.Series:
    import yfinance as yf
    df = yf.download("BZ=F", period="60d", interval="15m", progress=False, auto_adjust=False)
    s = df["Close"]["BZ=F"].dropna()
    s.index = pd.DatetimeIndex(s.index).tz_convert("UTC")
    return s.sort_index()

lco = load_lco(); lco_last = lco.index.max()
brent_yf = load_yf_brent()
print(f"LCO 1-min : {lco.index.min()} -> {lco_last}  ({len(lco):,} bars)")
print(f"yfinance  : {brent_yf.index.min()} -> {brent_yf.index.max()}  ({len(brent_yf):,} bars)")


# ## 4. Reaction windows
#
# `t0` = release timestamp. `p0` = last price at/just-before t0; `+2h`; `close` =
# last bar of the same UTC day. Returns are log-returns (×100 = %).

def reaction(price: pd.Series, t0: pd.Timestamp, hours: int = 2) -> dict:
    s  = price.dropna()
    p0 = s.asof(t0)
    p2 = s.asof(t0 + pd.Timedelta(hours=hours))
    end = t0.normalize() + pd.Timedelta(days=1)
    sd  = s[(s.index >= t0.normalize()) & (s.index < end)]
    pc  = sd.iloc[-1] if len(sd) else np.nan
    lr  = lambda a, b: np.log(b / a) if (a and b and a > 0 and b > 0) else np.nan
    return dict(p0=p0, p2h=p2, pclose=pc, ret_2h=lr(p0, p2), ret_close=lr(p0, pc))


# ## 5. Assemble the event table

rows = []
for _, r in crude.iterrows():
    t0 = r["release"]
    if pd.isna(r["actual"]):                              # upcoming release (kept for context)
        src, rx = "pending", dict(p0=np.nan, p2h=np.nan, pclose=np.nan, ret_2h=np.nan, ret_close=np.nan)
    elif t0 <= lco_last:
        src, rx = "LCO", reaction(lco["c1_mid"], t0)
    else:
        src, rx = "yfin", reaction(brent_yf, t0)
    m1m2 = np.nan                                         # term structure (backwardation) at release
    if t0 <= lco_last:
        sub = lco[lco.index <= t0]
        if len(sub) and pd.notna(sub.iloc[-1]["c2_mid"]):
            m1m2 = sub.iloc[-1]["c1_mid"] - sub.iloc[-1]["c2_mid"]
    rows.append({
        "release": t0, "crude_actual": r["actual"], "crude_fc": r["forecast"], "crude_surp": r["surprise"],
        "gas_chg":  (eia_at_release(gas_chg, t0)  if src != "pending" else np.nan),
        "dist_chg": (eia_at_release(dist_chg, t0) if src != "pending" else np.nan),
        "src": src, "ret_2h_%": 100 * rx["ret_2h"], "ret_close_%": 100 * rx["ret_close"],
        "p0": rx["p0"], "m1m2": m1m2,
    })
ev = pd.DataFrame(rows)
ev.to_parquet(CACHE / "event_table.parquet")
ev


# ## 6. What the dataset already shows
#
# Sign convention: **surprise > 0 = bigger build than expected = bearish**, so if
# inventories drove Brent we'd expect a **downward** slope (surprise↑ → reaction↓).

done = ev[ev.src.isin(["LCO", "yfin"])]
print(f"priced: {len(done)}/{len(ev)} "
      f"(LCO={sum(ev.src=='LCO')}, yfin={sum(ev.src=='yfin')}, pending={sum(ev.src=='pending')})")
print("missing reactions:", int(done[['ret_2h_%','ret_close_%']].isna().sum().sum()))
print("corr(surprise, ret_2h)   =", round(done['crude_surp'].corr(done['ret_2h_%']), 2))
print("corr(surprise, ret_close)=", round(done['crude_surp'].corr(done['ret_close_%']), 2))
print("M1-M2 (backwardation, $): min %.2f  max %.2f" % (ev['m1m2'].min(), ev['m1m2'].max()))

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].scatter(done["crude_surp"], done["ret_2h_%"])
ax[0].axhline(0, lw=.6, c="k"); ax[0].axvline(0, lw=.6, c="k")
ax[0].set(xlabel="crude surprise (M bbl, + = bearish)", ylabel="Brent +2h (%)",
          title="Inventory surprise vs 2h reaction")
ax[1].plot(done["release"], done["p0"], marker="o")
ax[1].set(title="Brent at each release (p0)", ylabel="$/bbl")
plt.tight_layout(); plt.show()


# ### Read-through (preliminary — not the model yet)
#
# - **16/17 releases priced**, zero missing reactions; tomorrow's release is `pending`.
# - The **surprise↔reaction correlation is weak / wrong-signed** in this window — i.e.
#   inventories were repeatedly *overridden*. The `p0` path shows why: Brent ran
#   ~\$80 → ~\$117 (late-Apr war premium) → ~\$77 now. A ±40% geopolitical regime
#   swamped a ±5 M bbl inventory signal. This is the core *"when inventories don't
#   matter"* evidence the framework is built to quantify.
# - The curve stayed in **steep backwardation (M1-M2 ≈ +3…+8)** throughout — a single
#   tight-market regime, so regime *variation* here is in the *level* of backwardation,
#   not contango↔backwardation flips.
#
# **Next (Step 1):** estimate Brent's macro betas (DXY, S&P) on daily data, strip them
# off the release-day reaction to get the **abnormal return**, then regress that on the
# crude surprise (+ product changes) — the actual inventory beta, market-controlled.
