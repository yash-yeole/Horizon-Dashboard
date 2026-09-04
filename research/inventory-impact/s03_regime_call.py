"""Step 2 - Regime call (war-premium regime dominates inventory)

Build + execute rough_work/03_step2_regime_call.ipynb (Step 2 / final).
Regime + amplifier layer, spread reactions (WTI-Brent, gasoil crack), and the
synthesis: bull/bear/neutral call, products/spreads, top-3 factors, framework.

Auto-extracted from _build_step2.py (was a notebook); run with the energy venv.
"""

# # Step 2 — **Regime, spreads & the call** (final)
#
# Steps 0–1 built the dataset and showed the market-controlled inventory beta is
# small and insignificant in this war regime. Step 2 finishes the job:
#
# 1. **Which products/spreads** react to a crude surprise — measured directly on the
#    ICE Brent (LCO), WTI (CL) and gas oil (LGO) 1-min tapes.
# 2. **Regime conditioning** — does the (weak) inventory signal break through in
#    high-vol / steep-backwardation weeks?
# 3. **Tomorrow's call** — bull / bear / neutral, the most-affected spread, the
#    **top-3 factors**, and a short **framework** write-up.

# ## 0. Setup — load event table + recompute the inventory beta (from Step 1)

import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
import yfinance as yf, matplotlib.pyplot as plt
ROOT  = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
REGD  = ROOT / "Regime/data"
pd.set_option("display.width", 200, "display.max_columns", 30, "display.float_format", lambda x: f"{x:,.3f}")

ev = pd.read_parquet(CACHE / "event_table.parquet")

# --- recompute the market-controlled inventory beta (compact Step-1 redo) ---
def daily_close(sym):
    s = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)["Close"][sym].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize(); return s
px  = pd.concat({"brent":daily_close("BZ=F"),"dxy":daily_close("DX-Y.NYB"),"spx":daily_close("^GSPC")},axis=1).dropna()
ret = np.log(px).diff().dropna(); ret = ret[ret.index >= "2026-03-01"]
mkt = sm.OLS(ret["brent"], sm.add_constant(ret[["dxy","spx"]])).fit(cov_type="HC3")
ret["abn"] = mkt.resid
ev["date"] = ev["release"].dt.tz_convert(None).dt.normalize()
ev = ev.merge((ret["abn"]*100).rename("abn_daily"), left_on="date", right_index=True, how="left")
d  = ev.dropna(subset=["crude_surp","abn_daily"]).copy()
A  = sm.OLS(d["abn_daily"], sm.add_constant(d["crude_surp"])).fit(cov_type="HC3")
B  = sm.OLS(d["abn_daily"], sm.add_constant(d[["crude_surp","gas_chg","dist_chg"]])).fit(cov_type="HC3")
BETA_A, BETA_B = A.params["crude_surp"], B.params["crude_surp"]
print(f"inventory beta: crude-only {BETA_A:+.3f} (p={A.pvalues['crude_surp']:.2f}) | "
      f"+products {BETA_B:+.3f} (p={B.pvalues['crude_surp']:.2f})")
print(f"events: {len(d)} | DXY beta {mkt.params['dxy']:+.2f} (p={mkt.pvalues['dxy']:.3f})")


# ## 1. Which products / spreads move? (LCO / CL / LGO 1-min)
#
# A crude (US) surprise should hit **WTI–Brent** (US-specific grade) and the
# **gas oil crack** differently from flat Brent. We measure each leg's price at
# `t0` and `t0+2h` and regress the spread change on the crude surprise. Uses the
# 1-min tapes (common coverage Mar → 20-May → 12 releases).

def load_c1(csv, cache, start="2026-02-20"):
    f = CACHE/cache
    if f.exists(): return pd.read_parquet(f)
    cols = ["timestamp","c1||weighted_mid"]
    raw = pd.read_csv(csv, comment="#", usecols=cols, dtype=str)
    raw = raw[raw["timestamp"] >= start]
    out = pd.DataFrame({"ts":pd.to_datetime(raw["timestamp"],utc=True),
                        "mid":pd.to_numeric(raw["c1||weighted_mid"],errors="coerce")}
                       ).dropna().set_index("ts").sort_index()["mid"]
    out.to_frame().to_parquet(f); return out.to_frame()

brent = load_c1(REGD/"LCO_data.csv","lco_c1.parquet")["mid"]   # $/bbl
wti   = load_c1(REGD/"CL_data.csv","cl_c1.parquet")["mid"]     # $/bbl
gasoil= load_c1(REGD/"LGO_data.csv","lgo_c1.parquet")["mid"]/7.45  # $/tonne -> $/bbl
last_common = min(brent.index.max(), wti.index.max(), gasoil.index.max())
print("common 1-min coverage ends:", last_common)

def at(s, t):  # price at/just-before t
    return s.asof(t)
def leg_react(s, t0, h=2):
    return at(s, t0+pd.Timedelta(hours=h)) - at(s, t0)

rows=[]
for _,r in ev.iterrows():
    t0=r["release"]
    if pd.isna(r["crude_surp"]) or t0 > last_common: continue
    b0,w0,g0 = at(brent,t0), at(wti,t0), at(gasoil,t0)
    rows.append({"release":t0.date(), "surp":r["crude_surp"],
        "dBrent": leg_react(brent,t0), "dWTI": leg_react(wti,t0),
        "dWTI_Brent": leg_react(wti,t0)-leg_react(brent,t0),       # WTI-Brent spread change
        "dGOcrack":  leg_react(gasoil,t0)-leg_react(brent,t0)})    # gasoil crack change
sp=pd.DataFrame(rows)
print(f"\nspread reactions over {len(sp)} releases (Mar->20-May), $ change in 2h:")
print(sp.round(3).to_string(index=False))

print("\nsensitivity to crude surprise  (beta = $ per Mbbl, corr in parens):")
for col in ["dBrent","dWTI","dWTI_Brent","dGOcrack"]:
    x=sm.add_constant(sp["surp"]); m=sm.OLS(sp[col],x).fit()
    print(f"  {col:11s} beta={m.params['surp']:+.3f}  (corr={sp['surp'].corr(sp[col]):+.2f}, p={m.pvalues['surp']:.2f})")


# ## 2. Regime conditioning — does the signal break through in high-vol weeks?

# trailing realized vol (10d) of Brent at each release
rv = ret["brent"].rolling(10).std()*100
ev = ev.merge(rv.rename("rvol10"), left_on="date", right_index=True, how="left")
dd = ev.dropna(subset=["crude_surp","abn_daily","rvol10"]).copy()
hi = dd[dd["rvol10"] >= dd["rvol10"].median()]; lo = dd[dd["rvol10"] < dd["rvol10"].median()]
print("corr(surprise, abnormal_return):")
print(f"  ALL  (n={len(dd)}): {dd['crude_surp'].corr(dd['abn_daily']):+.2f}")
print(f"  HIGH vol (n={len(hi)}): {hi['crude_surp'].corr(hi['abn_daily']):+.2f}")
print(f"  LOW  vol (n={len(lo)}): {lo['crude_surp'].corr(lo['abn_daily']):+.2f}")
print(f"\nbackwardation M1-M2 over sample: {ev['m1m2'].min():.1f} .. {ev['m1m2'].max():.1f} "
      f"(all positive -> permanently backwardated; tight-market regime, no contango weeks to contrast)")


# ## 3. Tomorrow's inputs — current state

brent_d = daily_close("BZ=F")
peak = brent_d.max(); now = brent_d.iloc[-1]
recent = ev.dropna(subset=["crude_actual"]).tail(5)[["date","crude_actual","crude_fc","crude_surp"]]
CONSENSUS, PREVIOUS = -5.1, float(ev.iloc[-1]["crude_fc"]) if False else -8.263
print(f"Brent now ${now:.1f} | 2026 peak ${peak:.1f}  -> {100*(now/peak-1):+.0f}% off peak (premium unwind)")
print(f"Tomorrow (24-Jun) consensus: {CONSENSUS:+.1f} M bbl | previous: {PREVIOUS:+.1f}")
print(f"Backwardation: steep & positive all window (M1-M2 up to ${ev['m1m2'].max():.1f}) = tight physical")
print("\nLast 5 releases (consensus chronically under-called the draws):")
print(recent.round(2).to_string(index=False))
print(f"\nmean surprise last 4 priced weeks: {ev.dropna(subset=['crude_surp']).tail(4)['crude_surp'].mean():+.2f} "
      "(negative = draws beating consensus = bullish surprises)")


# ## 4. The call

CONSENSUS = -5.1
print("="*64)
print("  TOMORROW'S EIA CRUDE RELEASE  ->  BRENT IMPACT CALL")
print("="*64)
print("\nHEADLINE:  NEUTRAL  (inventory is a secondary driver this regime)\n")
print("Inventory-driven Brent move by scenario (beta x surprise, regime drift excluded):")
for actual,lbl in [(-9,'big draw'),(-7,'solid draw'),(-5.1,'in-line'),(-3,'small draw'),(1,'build')]:
    s=actual-CONSENSUS
    print(f"  actual {actual:+5.1f} ({lbl:10s}) surprise {s:+4.1f}  ->  {BETA_B*s:+.2f}% Brent")
print(f"""
WHY NEUTRAL:
  - market-controlled inventory beta is small ({BETA_B:+.2f} %/Mbbl) and NOT
    significant (p>0.1) at N=16 -> low information content on its own.
  - consensus already expects a large draw (-5.1), so only an EXTREME print
    (draw > ~8 Mbbl, or an outright build) clears the noise band.
  - the dominant driver is the geopolitical risk-premium regime (Brent {100*(now/peak-1):+.0f}%
    off its peak); that swamps a +/-1% inventory wiggle.

ASYMMETRY / lean: recent draws keep beating consensus, so risk tilts mildly
  BULLISH *only* on a big draw; a surprise build would add to bearish momentum.

MOST-AFFECTED (see sec.1): WTI-Brent is the relative standout (|corr| 0.29 vs
  flat Brent 0.08) -- a US-specific print routes into the US grade -- but NO spread
  shows a statistically reliable response this regime; gas oil crack ~ nil.

TOP-3 FACTORS:
  1) Geopolitical risk-premium regime  -- dominant; sets direction, overrides inventory.
  2) Surprise vs the elevated -5.1 consensus  -- asymmetric; needs a big draw to be bullish.
  3) USD co-move (+ steep backwardation)  -- macro tailwind/headwind + tight-physical support.
""")


# ## 5. The framework (brief)
#
# **Goal.** Assess the likely Brent impact of a weekly EIA crude release — the
# *reaction*, not fair value.
#
# **1. Surprise, not level.** Markets price the *surprise* = `actual − consensus`.
# Consensus from Investing.com (free, keyless); actual validated against the EIA
# print (exact match, 16/16). Tomorrow's consensus −5.1 M bbl.
#
# **2. Two-stage, abnormal return.** With only ~16 releases since March we can't fit
# a fat regression, so: **(Stage 1)** estimate Brent's market betas (DXY, S&P) on
# ~80 daily points; **(Stage 2)** strip the market move off the release-day return
# to get the **abnormal return**, and regress *that* on the surprise (+ gasoline/
# distillate changes). The scarce events are spent only on the inventory coefficient.
#
# **3. Regime & amplifiers.** Condition on term-structure (backwardation), realized
# vol, and the dominant-news/geopolitical state — the layer that decides *when* the
# inventory signal breaks through vs gets overridden.
#
# **4. Products/spreads.** Measured directly on the LCO/CL/LGO 1-min tapes: of the
# complex, **WTI–Brent** is the most surprise-sensitive (|corr| 0.29 vs flat Brent
# 0.08) — a US-specific print routing into the US grade — though **no spread responds
# reliably** in this regime, and the **gas oil crack shows essentially none**.
#
# **Finding (this regime).** The inventory beta is the right sign (bigger build →
# lower Brent) but **small and insignificant** — Brent's ~35% round-trip on the war
# premium dominated. Hence **NEUTRAL** for tomorrow unless the surprise is extreme,
# with a mild bullish lean only on a large draw.
#
# ### Deliverables
# | Deliverable | Answer |
# |---|---|
# | **Bias** | **Neutral** (mild bullish lean only on a >~8 Mbbl draw; bearish on a build) |
# | **Products/spreads** | **WTI–Brent** most surprise-sensitive (US-specific print) > flat Brent; cracks ~nil — none reliable in this regime |
# | **Top-3 factors** | 1) geopolitical risk-premium regime · 2) surprise vs −5.1 consensus · 3) USD + backwardation |
# | **Framework** | surprise → two-stage abnormal-return event study → regime/amplifier overlay |
#
# *Caveats:* N≈16 (single war regime, by design); consensus is a free-calendar proxy
# for the true survey; reaction windows are +2h / same-day close.
