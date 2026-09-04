"""Predict the EIA weekly crude inventory change (OUR expected number).

The forecasting half of the framework: instead of reacting to the printed number,
build our own ex-ante estimate of the weekly commercial-crude stock change, train
& test it on ~10yr of history, and benchmark it against the Reuters consensus
(can we match/beat the street?). The surprise that drives the market reaction is
then actual - OUR_number (or actual - consensus); this script produces OUR_number.

Model = the EIA supply/demand balance identity, lagged so it is genuinely known
before the Wednesday release:
    dStock_t ~ implied_balance_{t-1} + dSPR_{t-1} + AR(dStock_{t-1,t-2}) + seasonality(t)
where implied_balance = production + imports - exports - refinery_inputs (Mbbl/wk).
Everything is lag-1: when we forecast week t's print, last week's (t-1) report is
the most recent data in hand. Run with the energy venv.
"""
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, httpx, statsmodels.api as sm

ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
pd.set_option("display.width", 220, "display.float_format", lambda x: f"{x:,.3f}")

def eia_key():
    for ln in (ROOT / "backend/.env").read_text().splitlines():
        if ln.startswith("HORIZON_EIA_API_KEY="):
            return ln.split("=", 1)[1].strip()
KEY = eia_key()

def eia(series_id, length=560):
    j = httpx.Client(timeout=40).get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                                     params={"api_key": KEY, "length": length}).json()["response"]["data"]
    s = pd.DataFrame(j)[["period", "value"]]
    s["period"] = pd.to_datetime(s["period"]); s["value"] = pd.to_numeric(s["value"])
    return s.sort_values("period").set_index("period")["value"]

# ── 1. assemble weekly fundamentals (period = week-ending Friday) ──
stocks = eia("PET.WCESTUS1.W")            # commercial crude stock LEVEL (kbbl)
prod   = eia("PET.WCRFPUS2.W")            # field production (kbbl/d)
imp    = eia("PET.WCEIMUS2.W")            # imports (kbbl/d)
exp    = eia("PET.WCREXUS2.W")            # exports (kbbl/d)
refin  = eia("PET.WCRRIUS2.W")            # refiner crude inputs (kbbl/d)
spr    = eia("PET.WCSSTUS1.W")            # SPR stock LEVEL (kbbl)

df = pd.DataFrame({"stocks": stocks, "prod": prod, "imp": imp, "exp": exp, "refin": refin, "spr": spr}).dropna()
df["dstock"] = df["stocks"].diff() / 1000.0                                   # M bbl W/W (TARGET)
df["implied_bal"] = (df["prod"] + df["imp"] - df["exp"] - df["refin"]) * 7 / 1000.0   # M bbl/wk
df["dspr"] = df["spr"].diff() / 1000.0                                        # M bbl W/W SPR
print(f"weekly data: {len(df)}  {df.index.min().date()} -> {df.index.max().date()}")
print(f"identity check: corr(dstock, implied_bal_same_week) = {df['dstock'].corr(df['implied_bal']):.3f}  "
      f"(contemporaneous; we only USE the lag)")

# ── 2. lag-1 feature matrix (everything known before the release) ──
woy = df.index.isocalendar().week.astype(float).values
feat = pd.DataFrame(index=df.index)
feat["bal_l1"]  = df["implied_bal"].shift(1)
feat["dspr_l1"] = df["dspr"].shift(1)
feat["ar1"]     = df["dstock"].shift(1)
feat["ar2"]     = df["dstock"].shift(2)
for h in (1, 2):
    feat[f"sin{h}"] = np.sin(2 * np.pi * h * woy / 52.0)
    feat[f"cos{h}"] = np.cos(2 * np.pi * h * woy / 52.0)
COLS = list(feat.columns)
y = df["dstock"]
data = feat.join(y).dropna()
print(f"modeling rows: {len(data)}")

# ── 3. expanding-window out-of-sample one-step-ahead forecast ──
START = 156   # ~3yr burn-in
pred = pd.Series(np.nan, index=data.index)
for i in range(START, len(data)):
    tr = data.iloc[:i]
    m = sm.OLS(tr["dstock"], sm.add_constant(tr[COLS])).fit()
    xi = data[COLS].iloc[[i]].copy(); xi.insert(0, "const", 1.0)
    pred.iloc[i] = float(m.predict(xi).iloc[0])
oos = data.assign(pred=pred).dropna(subset=["pred"])
err = oos["dstock"] - oos["pred"]

def stats(a, p):
    e = a - p
    rmse = np.sqrt((e ** 2).mean()); mae = e.abs().mean()
    r2 = 1 - (e ** 2).sum() / ((a - a.mean()) ** 2).sum()
    hit = (np.sign(a) == np.sign(p)).mean()
    return rmse, mae, r2, hit

# baselines
seas = pd.Series(index=oos.index, dtype=float)
woy_all = data.index.isocalendar().week.astype(int)
dstock_all = data["dstock"]
for t in oos.index:
    past = dstock_all[data.index < t]
    w = woy_all[data.index < t] == woy_all[data.index == t].iloc[0]
    seas[t] = past[w.values].mean() if w.sum() else past.mean()
naive_persist = oos["ar1"]                              # last week's change

print("\n=== OUT-OF-SAMPLE forecast skill (one-step-ahead, N_test={}) ===".format(len(oos)))
print(f"{'model':22s} {'RMSE':>7} {'MAE':>7} {'R2':>7} {'dir-hit':>8}")
for nm, p in [("OUR model", oos["pred"]), ("seasonal-naive", seas), ("persistence (last wk)", naive_persist)]:
    rmse, mae, r2, hit = stats(oos["dstock"], p)
    print(f"{nm:22s} {rmse:>7.2f} {mae:>7.2f} {r2:>+7.3f} {hit:>8.1%}")

# ── 4. benchmark vs the Reuters CONSENSUS on the overlap ──
cons = pd.read_csv(ROOT / "research/inventory-impact/WTI_consensus.csv")
for c in ["Actual", "Forecast"]:
    cons[c] = pd.to_numeric(cons[c].astype(str).str.replace("M", "").str.strip(), errors="coerce")
cons["rel"] = pd.to_datetime(cons["Release date"], format="%d-%m-%Y")
cons["week_end"] = (cons["rel"] - pd.Timedelta(days=5)).dt.normalize()
cons = cons.dropna(subset=["Forecast", "Actual"]).set_index("week_end").sort_index()
# align our OOS forecast to the consensus by nearest week-ending
comp = []
for we, row in cons.iterrows():
    pos = oos.index.get_indexer([we], method="nearest")[0]
    if pos < 0 or abs((oos.index[pos] - we).days) > 4:
        continue
    comp.append({"week": we, "actual": row["Actual"], "consensus": row["Forecast"],
                 "ours": oos["pred"].iloc[pos]})
comp = pd.DataFrame(comp).dropna()
print(f"\n=== OUR model vs REUTERS CONSENSUS (overlap N={len(comp)}, 2019+) ===")
print(f"{'forecaster':22s} {'RMSE':>7} {'MAE':>7} {'dir-hit':>8}")
for nm, col in [("OUR model", "ours"), ("Reuters consensus", "consensus")]:
    rmse, mae, r2, hit = stats(comp["actual"], comp[col])
    print(f"{nm:22s} {rmse:>7.2f} {mae:>7.2f} {hit:>8.1%}")
print(f"corr(ours, consensus)={comp['ours'].corr(comp['consensus']):.3f}  "
      f"corr(ours, actual)={comp['ours'].corr(comp['actual']):.3f}  "
      f"corr(consensus, actual)={comp['consensus'].corr(comp['actual']):.3f}")

# ── 4b. fixed chronological TRAIN/TEST split (validate the coefficients) ──
SPLIT = 0.70
cut = int(len(data) * SPLIT)
tr, te = data.iloc[:cut], data.iloc[cut:]
m_tr = sm.OLS(tr["dstock"], sm.add_constant(tr[COLS])).fit(cov_type="HC3")
xte = te[COLS].copy(); xte.insert(0, "const", 1.0)
pte = m_tr.predict(xte)                                       # frozen train coefficients on unseen test block
e_te = te["dstock"] - pte
r2_te = 1 - (e_te ** 2).sum() / ((te["dstock"] - te["dstock"].mean()) ** 2).sum()
hit_te = (np.sign(te["dstock"]) == np.sign(pte)).mean()
m_full = sm.OLS(data["dstock"], sm.add_constant(data[COLS])).fit()
print("\n=== Fixed chronological TRAIN/TEST split (coefficient validation) ===")
print(f"  split {SPLIT:.0%}/{1 - SPLIT:.0%}:  train {len(tr)} wks ({tr.index.min().date()} -> {tr.index.max().date()})  |  "
      f"test {len(te)} wks ({te.index.min().date()} -> {te.index.max().date()})")
print(f"  train R2={m_tr.rsquared:.3f}   ->   held-out TEST R2={r2_te:+.3f}   "
      f"(test RMSE={np.sqrt((e_te ** 2).mean()):.2f}, dir-hit={hit_te:.1%})")
print(f"  {'coef':8s} {'train_beta':>11} {'t-stat':>8} {'full_beta':>11}   (stability: train vs full sample)")
for c in COLS:
    print(f"  {c:8s} {m_tr.params[c]:>+11.3f} {m_tr.tvalues[c]:>+8.2f} {m_full.params[c]:>+11.3f}")

# ── 5. predict the 24-JUN release OUT-OF-SAMPLE (model never sees its actual) ──
# Target = week-ending 2026-06-19 (reported Wed 24-Jun). Train on every week BEFORE
# it; the Jun-19 row is held out entirely. Features are lag-1 (the Jun-12 report,
# the latest in hand on the morning of the 24-Jun release).
target_week = data.index.max()                       # 2026-06-19 (the 24-Jun print)
train = data[data.index < target_week]
xrow  = data[COLS].loc[[target_week]]
actual = float(data["dstock"].loc[target_week])

ours_model = sm.OLS(train["dstock"], sm.add_constant(train[COLS])).fit(cov_type="HC3")
xc = xrow.copy(); xc.insert(0, "const", 1.0)
point = float(ours_model.predict(xc).iloc[0])
resid_sd = float(np.std(ours_model.resid, ddof=len(COLS) + 1))

print("\n=== Validation design ===")
print(f"  total weekly obs: {len(data)} ({data.index.min().date()} -> {data.index.max().date()})")
print(f"  scheme: EXPANDING-WINDOW walk-forward (one-step-ahead OOS). Burn-in {START} wks "
      f"(~{START/len(data):.0%}); each later week predicted from a model fit on all weeks before it.")
print(f"  -> {len(oos)} genuinely out-of-sample weeks tested (~{len(oos)/len(data):.0%}). No row trains on its own value.")
print(f"  For the 24-Jun call specifically: trained on {len(train)} weeks (thru {train.index.max().date()}), "
      f"the Jun-19 target held out.")

print("\n=== Our equation (fit on training data thru 12-Jun, used for the 24-Jun call) ===")
print(f"  dStock = {ours_model.params['const']:+.2f}")
for c in COLS:
    t = ours_model.tvalues[c]; p = ours_model.pvalues[c]
    star = "***" if p < .01 else "**" if p < .05 else "*" if p < .1 else ""
    print(f"           {ours_model.params[c]:+.3f} * {c:8s}  t={t:+5.2f}  p={p:.3f} {star}")
print(f"  in-sample R2 = {ours_model.rsquared:.3f}   |   walk-forward OOS R2 = {stats(oos['dstock'], oos['pred'])[2]:+.3f}")

cons_2406 = -3.9                                      # Reuters consensus for the 24-Jun print
print(f"\n=== 24-JUN PREDICTION vs what actually happened ===")
print(f"  OUR prediction : {point:+.2f} M bbl   (+/-{resid_sd:.1f} 1sd)")
print(f"  Reuters cons.  : {cons_2406:+.2f} M bbl")
print(f"  ACTUAL (EIA)   : {actual:+.2f} M bbl")
print(f"  our error      : {actual - point:+.2f} M bbl   |   consensus error: {actual - cons_2406:+.2f} M bbl")
print(f"  -> {'OUR MODEL was closer' if abs(actual-point) < abs(actual-cons_2406) else 'consensus was closer'} "
      f"to the actual on this print.")
print(f"  drivers: implied balance(t-1)={xrow['bal_l1'].iloc[0]:+.1f}, dSPR(t-1)={xrow['dspr_l1'].iloc[0]:+.1f}, "
      f"last-wk change(ar1)={xrow['ar1'].iloc[0]:+.1f}, 2wk-ago(ar2)={xrow['ar2'].iloc[0]:+.1f}")
