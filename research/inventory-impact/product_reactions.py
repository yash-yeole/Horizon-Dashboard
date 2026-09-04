"""Product reaction study: do RBOB (gasoline) & HO (distillate) react to the EIA
release, and via which channel (own-product stock surprise vs crude spillover)?

The EIA Weekly Petroleum Status Report prints crude, gasoline and distillate
stocks together at 10:30 ET Wed. We already have the real Reuters consensus for
CRUDE (WTI_consensus.csv). No free product consensus history exists, so gasoline
& distillate surprises use the SAME lookahead-free model-expected baseline we
validated for crude (corr 0.92 vs real consensus): surprise = actual - expected,
expected = expanding harmonic-seasonal + AR(1-4).

Reaction = release-day return of RB=F / HO=F (and the RB-WTI, HO-WTI cracks),
macro-controlled, full sample + 2026 regime. Run with the energy venv.
"""
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, httpx, yfinance as yf, statsmodels.api as sm

ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
pd.set_option("display.width", 220, "display.float_format", lambda x: f"{x:,.3f}")

def eia_key():
    for ln in (ROOT / "backend/.env").read_text().splitlines():
        if ln.startswith("HORIZON_EIA_API_KEY="):
            return ln.split("=", 1)[1].strip()
KEY = eia_key()
def eia(sid, length=560):
    j = httpx.Client(timeout=40).get(f"https://api.eia.gov/v2/seriesid/{sid}",
                                     params={"api_key": KEY, "length": length}).json()["response"]["data"]
    s = pd.DataFrame(j)[["period", "value"]]
    s["period"] = pd.to_datetime(s["period"]); s["value"] = pd.to_numeric(s["value"])
    return s.sort_values("period").set_index("period")["value"]

# ── expanding model-expected surprise (seasonal + AR) for a weekly change ──
def expected_surprise(chg: pd.Series, min_train=104):
    woy = chg.index.isocalendar().week.astype(float).values
    X = pd.DataFrame(index=chg.index)
    X["const"] = 1.0
    for h in (1, 2):
        X[f"sin{h}"] = np.sin(2 * np.pi * h * woy / 52.0); X[f"cos{h}"] = np.cos(2 * np.pi * h * woy / 52.0)
    for L in (1, 2, 3, 4):
        X[f"lag{L}"] = chg.shift(L).values
    pred = np.full(len(chg), np.nan)
    for i in range(len(chg)):
        xi = X.iloc[[i]]
        if i < min_train or xi.isna().any().any():
            continue
        tr = X.iloc[:i].dropna(); ytr = chg.loc[tr.index]
        if len(tr) < 60:
            continue
        pred[i] = float(sm.OLS(ytr, tr).fit().predict(xi).iloc[0])
    return chg - pd.Series(pred, index=chg.index)            # surprise

gas_chg  = eia("PET.WGTSTUS1.W").diff() / 1000.0             # gasoline stock change, M bbl
dist_chg = eia("PET.WDISTUS1.W").diff() / 1000.0            # distillate stock change, M bbl
gas_surp = expected_surprise(gas_chg.dropna())
dist_surp = expected_surprise(dist_chg.dropna())
print(f"gasoline surprises: {gas_surp.notna().sum()}  distillate surprises: {dist_surp.notna().sum()}")

# ── crude surprise from REAL consensus, by release date ──
cons = pd.read_csv(ROOT / "research/inventory-impact/WTI_consensus.csv")
for c in ["Actual", "Forecast"]:
    cons[c] = pd.to_numeric(cons[c].astype(str).str.replace("M", "").str.strip(), errors="coerce")
cons["rel"] = pd.to_datetime(cons["Release date"], format="%d-%m-%Y").dt.normalize()
cons["week_end"] = (cons["rel"] - pd.Timedelta(days=5)).dt.normalize()
cons["crude_surp"] = cons["Actual"] - cons["Forecast"]
cons = cons.dropna(subset=["crude_surp"]).sort_values("rel")

# attach product surprises by nearest week-ending
def near(series, we):
    pos = series.index.get_indexer([we], method="nearest")[0]
    return series.iloc[pos] if abs((series.index[pos] - we).days) <= 4 else np.nan
cons["gas_surp"]  = cons["week_end"].map(lambda w: near(gas_surp, w))
cons["dist_surp"] = cons["week_end"].map(lambda w: near(dist_surp, w))

# ── prices: WTI, RBOB, HO daily; returns + cracks ($/bbl) ──
def dc(sym):
    x = yf.download(sym, period="8y", interval="1d", progress=False, auto_adjust=False)["Close"][sym].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x
wti = dc("CL=F"); rb = dc("RB=F"); ho = dc("HO=F"); dxy = dc("DX-Y.NYB"); spx = dc("^GSPC")
px = pd.concat({"wti": wti, "rb": rb, "ho": ho, "dxy": dxy, "spx": spx}, axis=1).dropna()
ret = np.log(px[["wti", "rb", "ho", "dxy", "spx"]]).diff() * 100
# cracks in $/bbl: RBOB & HO are $/gal -> x42
px["rb_crack"] = px["rb"] * 42 - px["wti"]
px["ho_crack"] = px["ho"] * 42 - px["wti"]
dcrack = px[["rb_crack", "ho_crack"]].diff()
print(f"price panel: {len(px)}  {px.index.min().date()} -> {px.index.max().date()}")

# ── release-day reaction ──
def on_release(rel, col, frame):
    fut = frame.index[frame.index >= rel]
    if len(fut) == 0:
        return np.nan
    return float(frame[col].loc[fut[0]])
for c, src in [("rb_ret", ("rb", ret)), ("ho_ret", ("ho", ret)), ("wti_ret", ("wti", ret)),
               ("dxy_ret", ("dxy", ret)), ("spx_ret", ("spx", ret)),
               ("rb_dcrack", ("rb_crack", dcrack)), ("ho_dcrack", ("ho_crack", dcrack))]:
    col, fr = src
    cons[c] = cons["rel"].map(lambda r: on_release(r, col, fr))
ev = cons.dropna(subset=["rb_ret", "ho_ret", "crude_surp"]).reset_index(drop=True)
print(f"event sample: N={len(ev)}  {ev.rel.min().date()} -> {ev.rel.max().date()}")

def fit(d, y, cols):
    d = d.dropna(subset=[y] + cols)
    return sm.OLS(d[y], sm.add_constant(d[cols])).fit(cov_type="HC3"), len(d)

def show(title, d, y, cols):
    m, n = fit(d, y, cols)
    parts = "  ".join(f"{c}={m.params[c]:+.3f}(p{m.pvalues[c]:.2f})" for c in cols)
    print(f"  {title:34s} N={n:>3} R2={m.rsquared:.2f}  {parts}")

print("\n=== PRODUCT reactions to inventory surprises (full sample, macro-controlled) ===")
show("RBOB ret ~ gasoline surp", ev, "rb_ret", ["gas_surp", "crude_surp", "dxy_ret", "spx_ret"])
show("HO ret   ~ distillate surp", ev, "ho_ret", ["dist_surp", "crude_surp", "dxy_ret", "spx_ret"])
show("WTI ret  ~ crude surp", ev, "wti_ret", ["crude_surp", "dxy_ret", "spx_ret"])
print("\n=== CRACK reactions ($/bbl change on release day) ===")
show("RB-WTI crack ~ gas & crude surp", ev, "rb_dcrack", ["gas_surp", "crude_surp"])
show("HO-WTI crack ~ dist & crude surp", ev, "ho_dcrack", ["dist_surp", "crude_surp"])

print("\n=== 2026 war regime only ===")
e26 = ev[ev.rel >= "2026-03-01"]
show("RBOB ret ~ gasoline surp", e26, "rb_ret", ["gas_surp", "crude_surp"])
show("HO ret   ~ distillate surp", e26, "ho_ret", ["dist_surp", "crude_surp"])

# ── OUR 24-Jun product forecasts: hold out the last row (wk-ending Jun-19) ──
print("\n=== OUR product number forecasts for the 24-Jun print (last row held out) ===")
for nm, chg in [("gasoline", gas_chg.dropna()), ("distillate", dist_chg.dropna())]:
    woy = chg.index.isocalendar().week.astype(float).values
    X = pd.DataFrame(index=chg.index); X["const"] = 1.0
    for h in (1, 2):
        X[f"sin{h}"] = np.sin(2 * np.pi * h * woy / 52.0); X[f"cos{h}"] = np.cos(2 * np.pi * h * woy / 52.0)
    for L in (1, 2, 3, 4):
        X[f"lag{L}"] = chg.shift(L).values
    target = chg.index.max()                                  # wk-ending Jun-19 = the 24-Jun print
    tr = X.iloc[:-1].dropna()                                 # train WITHOUT the Jun-19 row
    m = sm.OLS(chg.loc[tr.index], tr).fit(cov_type="HC3")
    xrow = X.loc[[target]]
    pt = float(m.predict(xrow).iloc[0])
    print(f"  {nm:11s} OUR predicted change: {pt:+.2f} M bbl   (seasonal woy={int(pd.Timestamp(target).isocalendar().week)}, "
          f"in-sample R2={m.rsquared:.2f})  [actual hidden for scoring]")
