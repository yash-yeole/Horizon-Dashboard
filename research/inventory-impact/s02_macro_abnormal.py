"""Step 1 - Macro market-model -> abnormal return -> inventory beta

Build + execute rough_work/02_step1_macro_abnormal.ipynb (Step 1).
Two-stage: macro market-model betas on daily data -> abnormal return on release
days -> market-controlled inventory regression. Run with the energy venv.

Auto-extracted from _build_step1.py (was a notebook); run with the energy venv.
"""

# # Step 1 — **Macro market-model → abnormal return → inventory beta**
#
# Step 0 showed the *raw* surprise↔reaction correlation is weak (+0.12). But a raw
# correlation mixes inventory with everything else moving Brent that day. Here we
# strip out the **market** component and isolate the inventory-attributable move.
#
# **Two-stage (handles the N≈16 problem):**
# 1. **Stage 1 — market model on daily data (~80 obs):** `BrentRet = β0 + β_dxy·DXYRet + β_spx·SPXRet + ε`.
#    DXY and S&P move every day, so these betas are well-identified.
# 2. **Stage 2 — abnormal return on release days (~16 obs):** `abnormal = residual ε` on the
#    release day = the move *not* explained by the market. Regress that on the crude
#    surprise (+ product changes). The scarce event rows are spent only on the
#    inventory coefficient.

# ## 0. Imports, config, load Step 0 event table

import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm
import matplotlib.pyplot as plt

ROOT  = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 200, "display.max_columns", 30,
              "display.float_format", lambda x: f"{x:,.3f}")

ev = pd.read_parquet(CACHE / "event_table.parquet")
print("event table:", ev.shape, "| priced:", int(ev.src.isin(['LCO','yfin']).sum()))
ev[["release","crude_surp","gas_chg","dist_chg","ret_2h_%","ret_close_%"]].tail(6)


# ## 1. Daily series & returns (Mar→now)
#
# Brent (`BZ=F`), DXY (`DX-Y.NYB`), S&P 500 (`^GSPC`). One risk proxy (S&P) +
# the dollar — deliberately just two factors to avoid the DXY/gold/VIX collinearity.

import yfinance as yf
def daily_close(sym):
    df = yf.download(sym, period="6mo", interval="1d", progress=False, auto_adjust=False)
    s = df["Close"][sym].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    return s

px  = pd.concat({"brent": daily_close("BZ=F"),
                 "dxy":   daily_close("DX-Y.NYB"),
                 "spx":   daily_close("^GSPC")}, axis=1).dropna()
ret = np.log(px).diff().dropna()
ret = ret[ret.index >= "2026-03-01"]
print(f"daily returns: {len(ret)} obs  {ret.index.min().date()} -> {ret.index.max().date()}")
ret.tail(3)


# ## 2. Stage 1 — market model (daily)

def report(model, name):
    print(f"=== {name} ===   N={int(model.nobs)}   R2={model.rsquared:.3f}   adjR2={model.rsquared_adj:.3f}")
    tbl = pd.DataFrame({"coef": model.params, "se": model.bse,
                        "t": model.tvalues, "p": model.pvalues})
    print(tbl.round(3).to_string()); print()

X1 = sm.add_constant(ret[["dxy", "spx"]])
m1 = sm.OLS(ret["brent"], X1).fit(cov_type="HC3")
report(m1, "Stage 1: BrentRet ~ DXYRet + SPXRet (daily)")
ret["abn"] = m1.resid                       # abnormal daily return (market-stripped)
print(f"Observed: beta_dxy={m1.params['dxy']:+.2f} (p={m1.pvalues['dxy']:.3f}), "
      f"beta_spx={m1.params['spx']:+.2f} (p={m1.pvalues['spx']:.3f}).")
print("In THIS Mar-Jun war regime Brent and the DOLLAR co-move POSITIVELY (both bid as")
print("geopolitical hedges) -- the usual negative oil/USD link inverted; equities show no")
print(f"reliable link. Market model R2={100*m1.rsquared:.0f}%; the remaining "
      f"{100*(1-m1.rsquared):.0f}% (incl. the geopolitical premium) stays in the abnormal return.")


# ## 3. Stage 2 — attach abnormal return to release days & regress on surprise
#
# `abn_daily` = the release-day abnormal return (%, market-stripped). We compare:
# **(A)** abnormal ~ crude surprise, **(B)** + product changes, **(C)** intraday 2h
# reaction ~ surprise (unadjusted cross-check from Step 0).

ev["date"] = ev["release"].dt.tz_convert(None).dt.normalize()
ev = ev.merge((ret["abn"] * 100).rename("abn_daily"), left_on="date", right_index=True, how="left")
ev = ev.merge((ret["brent"] * 100).rename("brent_day_%"), left_on="date", right_index=True, how="left")

d = ev.dropna(subset=["crude_surp", "abn_daily"]).copy()
print(f"usable events: {len(d)}\n")

A = sm.OLS(d["abn_daily"],  sm.add_constant(d["crude_surp"])).fit(cov_type="HC3")
B = sm.OLS(d["abn_daily"],  sm.add_constant(d[["crude_surp","gas_chg","dist_chg"]])).fit(cov_type="HC3")
C = sm.OLS(d["ret_2h_%"],   sm.add_constant(d["crude_surp"])).fit(cov_type="HC3")
report(A, "A) abnormal_daily ~ crude_surp  (market-controlled)")
report(B, "B) abnormal_daily ~ crude_surp + gas_chg + dist_chg")
report(C, "C) intraday ret_2h ~ crude_surp  (unadjusted cross-check)")


# ## 4. Picture & comparison vs the raw correlation

print("crude-surprise beta (%/Mbbl):")
print(f"  raw daily Brent ~ surp : {sm.OLS(d['brent_day_%'], sm.add_constant(d['crude_surp'])).fit().params['crude_surp']:+.3f}")
print(f"  market-controlled (A)  : {A.params['crude_surp']:+.3f}   (p={A.pvalues['crude_surp']:.2f})")
print(f"  intraday 2h (C)        : {C.params['crude_surp']:+.3f}   (p={C.pvalues['crude_surp']:.2f})")
print("\nExpected sign is NEGATIVE (bigger build = bearish). "
      "Significance with N=16 is the real test.")

fig, ax = plt.subplots(1, 2, figsize=(12, 4))
ax[0].scatter(d["crude_surp"], d["abn_daily"])
xs = np.linspace(d["crude_surp"].min(), d["crude_surp"].max(), 50)
ax[0].plot(xs, A.params["const"] + A.params["crude_surp"]*xs, "r--")
ax[0].axhline(0, lw=.6, c="k"); ax[0].axvline(0, lw=.6, c="k")
ax[0].set(xlabel="crude surprise (M bbl, + = bearish)", ylabel="abnormal daily return (%)",
          title="Market-controlled inventory reaction")
ax[1].scatter(d["crude_surp"], d["ret_2h_%"], c="tab:orange")
ax[1].axhline(0, lw=.6, c="k"); ax[1].axvline(0, lw=.6, c="k")
ax[1].set(xlabel="crude surprise (M bbl)", ylabel="intraday +2h (%)", title="Intraday cross-check")
plt.tight_layout(); plt.show()


# ## 5. What this implies for tomorrow (sets up Step 3)

CONSENSUS = -5.1   # ForexFactory consensus for the 24-Jun release (M bbl)
beta, betaB = A.params["crude_surp"], B.params["crude_surp"]
print("Inventory sensitivity (market-controlled):")
print(f"  A) crude only      : {beta:+.3f} %/Mbbl  (p={A.pvalues['crude_surp']:.2f})")
print(f"  B) + product ctrls : {betaB:+.3f} %/Mbbl  (p={B.pvalues['crude_surp']:.2f})")
print(f"\nCAUTION: model intercept ({A.params['const']:+.2f}%) = average release-day drift while")
print("Brent was falling (REGIME), NOT an inventory effect. We do NOT extrapolate it as a")
print("forecast; the regime is handled in Step 2. Only the SLOPE is the inventory part.\n")
print("Inventory-DRIVEN component of tomorrow's move = beta x surprise:")
for actual in [-11, -9, -7, -5.1, -3, -1, 1]:
    surp = actual - CONSENSUS
    tag  = "in-line" if abs(surp) < 0.6 else ("bullish surprise" if surp < 0 else "bearish surprise")
    print(f"  actual {actual:+5.1f} -> surprise {surp:+5.1f} -> inv move {beta*surp:+.2f}% (A) / "
          f"{betaB*surp:+.2f}% (B)   ({tag})")
print("\nEven a large surprise yields a <~1.5% inventory move, and the beta is NOT significant")
print("at N=16 -> base case = MUTED/neutral inventory reaction; the regime dominates.")


# ### Read-through
#
# - **Stage 1** betas are *unconventional this regime*: Brent and the **dollar co-move
#   positively** (both bid as geopolitical hedges — the usual negative oil/USD link inverted),
#   equities show no reliable link, and the market model explains only ~28% of daily Brent.
#   The **geopolitical premium is not DXY or S&P**, so it survives into the abnormal return —
#   *why* even a controlled inventory beta stays weak here.
# - **Stage 2** is the headline: the market-controlled crude-surprise beta and its p-value
#   tell us whether inventories moved Brent *after* removing the market. Small/insignificant
#   ⇒ the base case for tomorrow is a **muted/neutral** inventory reaction.
# - **Next (Step 2):** regime & amplifier layer — split by backwardation level / vol, and
#   add the dominant-news flag, to pin down *when* the (weak) inventory signal does break
#   through, and finalize tomorrow's bull/bear/neutral call + top-3 factors.
