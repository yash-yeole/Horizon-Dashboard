"""Step 3 - Out-of-sample validation (3 ways)

Build + execute rough_work/04_validation.ipynb.
Out-of-sample validation of the inventory-surprise model: LOOCV, expanding
walk-forward, and a 70/30 temporal holdout. Skill is measured vs an
intercept-only (predict-the-mean) baseline. Run with the energy venv.

Auto-extracted from _build_validation.py (was a notebook); run with the energy venv.
"""

# # Step 3 — **Out-of-sample validation**
#
# Steps 0–2 reported *in-sample* fit. Here we test whether the inventory **surprise**
# actually **predicts** out-of-sample, against an honest baseline.
#
# - **N=16** releases -> a single 70/30 holdout = train 11 / test 5 (thin). So the
#   primary tests are **leave-one-out CV (LOOCV)** and **expanding walk-forward**
#   (train on the past, predict the next release — no look-ahead). The 70/30 holdout
#   is shown too for completeness.
# - **Baseline = intercept-only** (predict the training mean). A model has skill only
#   if it beats that baseline out-of-sample. Skill-R² = 1 − SS_model / SS_baseline
#   (>0 = beats the mean; <0 = worse than the mean).
# - Targets: **abnormal daily return** (market-controlled, the model's target) and the
#   **intraday +2h** reaction (leakage-free: depends on no estimated betas).
# - Models: **A** = surprise · **B** = surprise + gasoline + distillate.

# ## 0. Rebuild the modelling frame (event table + abnormal return)

import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm, yfinance as yf
ROOT  = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 200, "display.float_format", lambda x: f"{x:,.3f}")

ev = pd.read_parquet(CACHE / "event_table.parquet")
def daily_close(s):
    x = yf.download(s, period="6mo", interval="1d", progress=False, auto_adjust=False)["Close"][s].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px  = pd.concat({"brent":daily_close("BZ=F"),"dxy":daily_close("DX-Y.NYB"),"spx":daily_close("^GSPC")},axis=1).dropna()
ret = np.log(px).diff().dropna(); ret = ret[ret.index >= "2026-03-01"]
ret["abn"] = sm.OLS(ret["brent"], sm.add_constant(ret[["dxy","spx"]])).fit().resid
ev["date"] = ev["release"].dt.tz_convert(None).dt.normalize()
ev = ev.merge((ret["abn"]*100).rename("abn_daily"), left_on="date", right_index=True, how="left")

d = ev.dropna(subset=["crude_surp","abn_daily"]).sort_values("release").reset_index(drop=True)
print(f"events for validation: N={len(d)}  ({d['release'].dt.date.min()} -> {d['release'].dt.date.max()})")
print("in-sample R2 for reference: "
      f"A={sm.OLS(d['abn_daily'], sm.add_constant(d['crude_surp'])).fit().rsquared:.3f}  "
      f"B={sm.OLS(d['abn_daily'], sm.add_constant(d[['crude_surp','gas_chg','dist_chg']])).fit().rsquared:.3f}")


# ## 1. Validation engine (LOOCV / walk-forward / 70-30) vs predict-the-mean

MIN_TRAIN = 8

def oos_predict(df, feats, target, scheme):
    y = df[target].to_numpy(); n = len(df); pred = np.full(n, np.nan)
    if   scheme == "loo":     splits = [(np.arange(n) != i, i) for i in range(n)]
    elif scheme == "wf":      splits = [(np.arange(n) <  t, t) for t in range(MIN_TRAIN, n)]
    elif scheme == "holdout": cut = int(round(0.7*n)); splits = [(np.arange(n) < cut, j) for j in range(cut, n)]
    for trmask, te in splits:
        ytr = y[trmask]
        if not feats:                       # intercept-only baseline
            pred[te] = ytr.mean()
        else:
            Xtr = sm.add_constant(df.loc[trmask, feats], has_constant="add")
            m   = sm.OLS(ytr, Xtr).fit()
            xte = df.loc[[te], feats].copy(); xte.insert(0, "const", 1.0)
            pred[te] = float(m.predict(xte).iloc[0])
    return pred, y

def score(df, target, scheme):
    base,_ = oos_predict(df, [],                                  target, scheme)
    pA,y   = oos_predict(df, ["crude_surp"],                      target, scheme)
    pB,_   = oos_predict(df, ["crude_surp","gas_chg","dist_chg"], target, scheme)
    m = np.isfinite(pA)                      # evaluate only on predicted points
    y, base, pA, pB = y[m], base[m], pA[m], pB[m]
    def rmse(p): return np.sqrt(np.mean((y-p)**2))
    def skill(p): return 1 - np.sum((y-p)**2)/np.sum((y-base)**2)
    def hit(p):  return np.mean(np.sign(p) == np.sign(y))
    return dict(n_test=len(y),
                rmse_base=rmse(base), rmse_A=rmse(pA), rmse_B=rmse(pB),
                skillR2_A=skill(pA), skillR2_B=skill(pB),
                hit_A=hit(pA), hit_B=hit(pB))


# ## 2. Results — does the surprise predict out-of-sample?

for target in ["abn_daily", "ret_2h_%"]:
    print(f"\n######## TARGET = {target} ########")
    rows = {sc: score(d, target, sc) for sc in ["loo", "wf", "holdout"]}
    tbl = pd.DataFrame(rows).T
    tbl.index = ["LOOCV", "walk-forward", "holdout 70/30"]
    print(tbl[["n_test","rmse_base","rmse_A","rmse_B","skillR2_A","skillR2_B","hit_A","hit_B"]].round(3).to_string())
    print("  (skillR2 > 0 => beats predict-the-mean; rmse_A/B < rmse_base => model helps; hit ~0.5 => no directional edge)")


# ## 3. Read-through
#
# Interpretation guide:
# - **skillR2_A / skillR2_B ≤ 0** ⇒ adding the inventory surprise does **not** beat
#   simply predicting the mean out-of-sample — i.e. **no predictive skill**.
# - **rmse_A ≥ rmse_base** ⇒ same conclusion in error terms.
# - **hit ≈ 0.5** ⇒ the model gets the *direction* right no better than a coin flip.
#
# Given the in-sample beta was already small and insignificant (Step 1), we expect the
# OOS validation to confirm **no reliable predictive power in this war regime** — which
# is exactly why the call is **NEUTRAL**. A model that honestly fails to predict here is
# the correct result, not a bug: it says *the inventory print is not the thing moving
# Brent right now*. The framework would need a quieter-regime sample (more releases,
# no dominant geopolitical premium) to show a significant, validated inventory beta.
