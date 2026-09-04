"""Audit: the WTI crude REACTION regression with ALL discussed factors.

The reaction model we have been quoting is just:
    wti_day ~ crude_surprise + DXY + SPX
This script re-states that exact equation AND adds the other factors we discussed
across the project, to test empirically whether any of them change the inventory
beta or belong in the spec:
  - realized vol (20d trailing WTI)         [available 7yr]
  - gasoline & distillate stock surprises   [available 7yr, model-expected]
  - news Delta-tone (GDELT)                 [war-regime cache only]
  - backwardation M1-M2                      [war-regime event table only, Brent proxy]
Run with the energy venv.
"""
import warnings, json
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, httpx, yfinance as yf, statsmodels.api as sm

ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 240, "display.float_format", lambda x: f"{x:,.3f}")

def eia_key():
    for ln in (ROOT / "backend/.env").read_text().splitlines():
        if ln.startswith("HORIZON_EIA_API_KEY="):
            return ln.split("=", 1)[1].strip()
KEY = eia_key()
def eia(sid, length=560):
    j = httpx.Client(timeout=40).get(f"https://api.eia.gov/v2/seriesid/{sid}",
                                     params={"api_key": KEY, "length": length}).json()["response"]["data"]
    s = pd.DataFrame(j)[["period", "value"]]; s["period"] = pd.to_datetime(s["period"]); s["value"] = pd.to_numeric(s["value"])
    return s.sort_values("period").set_index("period")["value"]

def expected_surprise(chg, min_train=104):
    woy = chg.index.isocalendar().week.astype(float).values
    X = pd.DataFrame(index=chg.index); X["const"] = 1.0
    for h in (1, 2):
        X[f"sin{h}"] = np.sin(2*np.pi*h*woy/52); X[f"cos{h}"] = np.cos(2*np.pi*h*woy/52)
    for L in (1, 2, 3, 4):
        X[f"lag{L}"] = chg.shift(L).values
    pred = np.full(len(chg), np.nan)
    for i in range(len(chg)):
        xi = X.iloc[[i]]
        if i < min_train or xi.isna().any().any(): continue
        tr = X.iloc[:i].dropna()
        if len(tr) < 60: continue
        pred[i] = float(sm.OLS(chg.loc[tr.index], tr).fit().predict(xi).iloc[0])
    return chg - pd.Series(pred, index=chg.index)

# crude surprise (real consensus) + release dates
cons = pd.read_csv(ROOT / "research/inventory-impact/WTI_consensus.csv")
for c in ["Actual", "Forecast"]:
    cons[c] = pd.to_numeric(cons[c].astype(str).str.replace("M", "").str.strip(), errors="coerce")
cons["rel"] = pd.to_datetime(cons["Release date"], format="%d-%m-%Y").dt.normalize()
cons["week_end"] = (cons["rel"] - pd.Timedelta(days=5)).dt.normalize()
cons["crude_surp"] = cons["Actual"] - cons["Forecast"]
cons = cons.dropna(subset=["crude_surp"]).sort_values("rel")

gas_surp  = expected_surprise((eia("PET.WGTSTUS1.W").diff()/1000).dropna())
dist_surp = expected_surprise((eia("PET.WDISTUS1.W").diff()/1000).dropna())
def near(s, we):
    p = s.index.get_indexer([we], method="nearest")[0]
    return s.iloc[p] if abs((s.index[p]-we).days) <= 4 else np.nan
cons["gas_surp"]  = cons["week_end"].map(lambda w: near(gas_surp, w))
cons["dist_surp"] = cons["week_end"].map(lambda w: near(dist_surp, w))

# prices + realized vol
def dc(sym):
    x = yf.download(sym, period="8y", interval="1d", progress=False, auto_adjust=False)["Close"][sym].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px = pd.concat({"wti": dc("CL=F"), "dxy": dc("DX-Y.NYB"), "spx": dc("^GSPC")}, axis=1).dropna()
ret = np.log(px).diff() * 100
rvol = ret["wti"].rolling(20).std()
def onrel(rel, s):
    fut = s.index[s.index >= rel]
    return float(s.loc[fut[0]]) if len(fut) else np.nan
for nm, s in [("wti_day", ret["wti"]), ("dxy_day", ret["dxy"]), ("spx_day", ret["spx"]), ("rvol", rvol.shift(1))]:
    cons[nm] = cons["rel"].map(lambda r: onrel(r, s))
ev = cons.dropna(subset=["wti_day", "crude_surp"]).reset_index(drop=True)

def eq(d, y, cols, title):
    d = d.dropna(subset=[y] + cols)
    m = sm.OLS(d[y], sm.add_constant(d[cols])).fit(cov_type="HC3")
    print(f"\n{title}  (N={len(d)}, R2={m.rsquared:.3f})")
    print(f"   {y} = {m.params['const']:+.3f}")
    for c in cols:
        st = "***" if m.pvalues[c] < .01 else "**" if m.pvalues[c] < .05 else "*" if m.pvalues[c] < .1 else ""
        print(f"          {m.params[c]:+.3f} * {c:11s}  t={m.tvalues[c]:+5.2f}  p={m.pvalues[c]:.3f} {st}")
    return m

print("=" * 70)
print("FULL 7-YEAR WTI CRUDE REACTION REGRESSIONS")
print("=" * 70)
eq(ev, "wti_day", ["crude_surp"], "M0  current 'inventory beta' (no controls)")
eq(ev, "wti_day", ["crude_surp", "dxy_day", "spx_day"], "M1  CURRENT SPEC (macro-controlled)")
eq(ev, "wti_day", ["crude_surp", "dxy_day", "spx_day", "rvol"], "M2  + realized vol")
eq(ev, "wti_day", ["crude_surp", "dxy_day", "spx_day", "rvol", "gas_surp", "dist_surp"],
   "M3  + product surprises (gasoline, distillate)")

# ── war-regime add-ons: news Delta-tone + backwardation ──
print("\n" + "=" * 70)
print("WAR-REGIME (2026) WTI REACTION + news tone & backwardation")
print("=" * 70)
tone = pd.DataFrame(json.loads((CACHE/"gdelt_oiltone.json").read_text())["timeline"][0]["data"])
tone["date"] = pd.to_datetime(tone["date"].str[:8]); dtone = tone.set_index("date")["value"].diff()
etab = pd.read_parquet(CACHE/"event_table.parquet").dropna(subset=["crude_actual"]).copy()
etab["date"] = etab["release"].dt.tz_convert(None).dt.normalize()
e26 = ev[ev.rel >= "2026-03-01"].copy()
e26["dtone"] = e26["rel"].map(lambda r: dtone.reindex([pd.Timestamp(r)]).iloc[0] if pd.Timestamp(r) in dtone.index else np.nan)
e26 = e26.merge(etab[["date", "m1m2"]].rename(columns={"m1m2": "backwardation"}), left_on="rel", right_on="date", how="left")
eq(e26, "wti_day", ["crude_surp", "dxy_day", "spx_day"], "W1  war-regime macro-controlled")
eq(e26.dropna(subset=["dtone"]), "wti_day", ["crude_surp", "dxy_day", "spx_day", "dtone"], "W2  + news Delta-tone")
eq(e26.dropna(subset=["backwardation"]), "wti_day", ["crude_surp", "backwardation"], "W3  + backwardation (Brent M1-M2 proxy)")
print("\n(news tone & backwardation are war-regime-only: GDELT tone cache + CL/LCO term structure")
print(" are not assembled over the full 7yr; they were studied as overlays, not 7yr regressors.)")
