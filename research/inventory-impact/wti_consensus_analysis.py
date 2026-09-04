"""WTI + consensus re-estimation (the honest instrument switch).

Two corrections vs the prior Brent/API build:
  1. Reaction instrument: WTI (CL) not Brent (LCO/BZ) -- EIA measures *US* crude
     inventories, WTI is the US barrel; Brent carries global/geopolitical drivers
     (e.g. the war-hedge DXY inversion) that are NOT inventory-attributable.
  2. Surprise anchor: EIA - consensus (Reuters poll via Investing 'Forecast' =
     event_table.crude_surp) not EIA - API. Desk wants the published consensus
     the market trades against, not the often-wrong API number.

Re-fits Stage 1 (macro abnormal return on WTI), Stage 2 (inventory beta on
EIA-consensus), the standardized top-3 driver ranking, and LOOCV -- all on WTI.
Run with the energy venv python. Prints the new production snapshot numbers."""
import warnings, json
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm, yfinance as yf

ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 200, "display.float_format", lambda x: f"{x:,.3f}")

# ── event table: crude_surp is ALREADY EIA - consensus (the anchor we want) ──
ev = pd.read_parquet(CACHE / "event_table.parquet")
ev["date"] = ev["release"].dt.tz_convert(None).dt.normalize()
done = ev.dropna(subset=["crude_actual"]).copy()
print(f"completed events: {len(done)}  ({done['date'].min().date()} -> {done['date'].max().date()})")

# ── recompute the reaction on WTI: CL 1-min intraday, yfinance CL=F 15m for the gap ──
cl = pd.read_parquet(CACHE / "cl_c1.parquet")["mid"]
cl_last = cl.index.max()
clf = yf.download("CL=F", period="60d", interval="15m", progress=False, auto_adjust=False)["Close"]["CL=F"].dropna()
clf.index = pd.to_datetime(clf.index).tz_convert("UTC")
print(f"WTI intraday: cl_c1 to {cl_last}, CL=F 15m from {clf.index.min()} ({len(clf)} bars)")

def wti_react(t0, hrs):
    s = (cl if t0 <= cl_last else clf).dropna()
    p0 = s.asof(t0); p1 = s.asof(t0 + pd.Timedelta(hours=hrs))
    return 100 * np.log(p1 / p0) if (p0 and p1 and p0 > 0 and p1 > 0) else np.nan

done["wti_2h"] = done["release"].map(lambda t: wti_react(t, 2))
done["wti_6h"] = done["release"].map(lambda t: wti_react(t, 6))
print("\nWTI reaction recomputed (was Brent):")
print(done[["date", "crude_actual", "crude_fc", "crude_surp", "ret_2h_%", "wti_2h", "wti_6h"]]
      .rename(columns={"ret_2h_%": "brent_2h"}).round(3).to_string(index=False))

# ── Stage 1: macro market-model on WTI daily -> abnormal return ──
tone = pd.DataFrame(json.loads((CACHE / "gdelt_oiltone.json").read_text())["timeline"][0]["data"])
tone["date"] = pd.to_datetime(tone["date"].str[:8])
dtone = tone.set_index("date")["value"].diff().rename("dtone")

def dc(s):
    x = yf.download(s, period="1y", interval="1d", progress=False, auto_adjust=False)["Close"][s].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x

px = pd.concat({"wti": dc("CL=F"), "dxy": dc("DX-Y.NYB"), "spx": dc("^GSPC")}, axis=1).dropna()
ret = np.log(px).diff().dropna().join(dtone, how="inner").dropna()
war = ret[ret.index >= "2026-03-01"]
print(f"\nwar-regime daily WTI obs: {len(war)}  ({war.index.min().date()} -> {war.index.max().date()})")

mac = sm.OLS(war["wti"], sm.add_constant(war[["dxy", "spx"]])).fit()
ret["abn"] = sm.OLS(ret["wti"], sm.add_constant(ret[["dxy", "spx"]])).fit().resid * 100
done = done.merge(ret["abn"].rename("abn_daily"), left_on="date", right_index=True, how="left")
print(f"Stage-1 macro (WTI~DXY+SPX): dxy beta {mac.params['dxy']:+.2f} (p={mac.pvalues['dxy']:.3f}), "
      f"spx beta {mac.params['spx']:+.2f} (p={mac.pvalues['spx']:.3f}), R2={mac.rsquared:.3f}")

# ── Stage 2: inventory beta on EIA - consensus (WTI targets) ──
def loocv(df, cols, y):
    df = df.reset_index(drop=True); yy = df[y]; n = len(df); pr = np.full(n, np.nan)
    for i in range(n):
        tr = [j for j in range(n) if j != i]
        m = sm.OLS(yy.iloc[tr], sm.add_constant(df.loc[tr, cols], has_constant="add")).fit()
        xi = df.loc[[i], cols].copy(); xi.insert(0, "const", 1.0); pr[i] = float(m.predict(xi).iloc[0])
    base = np.array([yy.iloc[[j for j in range(n) if j != i]].mean() for i in range(n)])
    return 1 - np.sum((yy.values - pr) ** 2) / np.sum((yy.values - base) ** 2)

print("\n=== Stage 2: inventory beta on EIA-consensus surprise (WTI) ===")
for tgt in ["wti_2h", "wti_6h", "abn_daily"]:
    d = done.dropna(subset=["crude_surp", tgt]).reset_index(drop=True)
    m = sm.OLS(d[tgt], sm.add_constant(d["crude_surp"])).fit()
    oos = loocv(d, ["crude_surp"], tgt) if len(d) > 4 else float("nan")
    print(f"  {tgt:9s} N={len(d):2d}  beta={m.params['crude_surp']:+.3f} %/Mbbl  "
          f"p={m.pvalues['crude_surp']:.2f}  R2={m.rsquared:.3f}  OOS={oos:+.3f}")

# ── standardized top-3 driver ranking on WTI daily ──
print("\n=== Top-3 daily WTI drivers (war regime, standardized) ===")
X = war[["dxy", "spx", "dtone"]]; y = war["wti"]
mm = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC3")
rows = []
for c in X.columns:
    rows.append({"factor": c, "coef": mm.params[c], "p": mm.pvalues[c],
                 "std_beta": mm.params[c] * X[c].std() / y.std()})
rank = pd.DataFrame(rows); rank["abs"] = rank["std_beta"].abs()
rank = rank.sort_values("abs", ascending=False).drop(columns="abs").reset_index(drop=True)
labels = {"dtone": "News / geopolitical sentiment", "dxy": "US dollar (DXY)", "spx": "Equities / risk (S&P 500)"}
print(f"full daily model R2={mm.rsquared:.3f}")
for i, r in rank.iterrows():
    print(f"  {i+1}. {labels[r['factor']]:32s} std-beta {r['std_beta']:+.2f}  (coef {r['coef']:+.2f}, p={r['p']:.2f})")

print("\n=== PRODUCTION SNAPSHOT (paste into release_impact.py) ===")
d2 = done.dropna(subset=["crude_surp", "wti_2h"]).reset_index(drop=True)
mb = sm.OLS(d2["wti_2h"], sm.add_constant(d2["crude_surp"])).fit()
print(f"_INVENTORY_BETA = {mb.params['crude_surp']:.3f}   # WTI +2h on EIA-consensus, p={mb.pvalues['crude_surp']:.2f}")
print("_TOP_FACTORS (WTI):")
for i, r in rank.iterrows():
    print(f'    ("{labels[r["factor"]]}", {r["std_beta"]:+.2f}, {r["p"]:.3f}),')
