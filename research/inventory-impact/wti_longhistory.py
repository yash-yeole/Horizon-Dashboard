"""7-year WTI inventory event study on the REAL Reuters consensus.

Desk-grade version of _wti_longhistory.py: the model-expected surprise proxy is
replaced by the actual published consensus (rough_work/WTI_consensus, 390 releases
2019-01 -> 2026-06, Forecast = Reuters poll). surprise = Actual - Forecast.
The CSV gives the exact release DATE, so no week-ending->Wednesday mapping is
needed. Reaction window stays DAILY (intraday isn't free that far back):
release-day abnormal return + 2-day CAR. Run with the energy venv.
"""
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm

ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 220, "display.float_format", lambda x: f"{x:,.3f}")

# ── 1. real consensus CSV -> surprise = Actual - Forecast ──
df = pd.read_csv(ROOT / "research/inventory-impact/WTI_consensus.csv")
for c in ["Actual", "Forecast", "Previous"]:
    df[c] = pd.to_numeric(df[c].astype(str).str.replace("M", "").str.strip(), errors="coerce")
df["date"] = pd.to_datetime(df["Release date"], format="%d-%m-%Y").dt.normalize()
df = df.dropna(subset=["Actual", "Forecast"]).sort_values("date").reset_index(drop=True)
df["surprise"] = df["Actual"] - df["Forecast"]            # + = bigger build than consensus = bearish
print(f"real consensus: N={len(df)}  {df.date.min().date()} -> {df.date.max().date()}  "
      f"surprise std={df.surprise.std():.2f}")

# ── 2. WTI daily + macro (DXY, SPX) ──
def dc(sym):
    x = yf.download(sym, period="8y", interval="1d", progress=False, auto_adjust=False)["Close"][sym].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px = pd.concat({"wti": dc("CL=F"), "dxy": dc("DX-Y.NYB"), "spx": dc("^GSPC")}, axis=1).dropna()
ret = np.log(px).diff().dropna()
print(f"WTI daily returns: {len(ret)}  {ret.index.min().date()} -> {ret.index.max().date()}")

# ── 3. reaction on the exact release date (+ 2-day CAR) ──
def react(rel):
    fut = ret.index[ret.index >= rel]
    if len(fut) == 0:
        return (np.nan,) * 4
    i0 = ret.index.get_loc(fut[0])
    r0 = ret["wti"].iloc[i0] * 100
    car = r0 + (ret["wti"].iloc[i0 + 1] * 100 if i0 + 1 < len(ret) else 0.0)
    return r0, car, ret["dxy"].iloc[i0] * 100, ret["spx"].iloc[i0] * 100

ev = df.copy()
ev[["wti_day", "wti_car2", "dxy_day", "spx_day"]] = pd.DataFrame(ev["date"].map(react).tolist(), index=ev.index)
ev = ev.dropna(subset=["wti_day", "surprise"]).reset_index(drop=True)
ev = ev[ev["date"] >= "2019-01-01"].reset_index(drop=True)
print(f"event sample (priced): N={len(ev)}  {ev.date.min().date()} -> {ev.date.max().date()}")

def fit(d, y, cols):
    return sm.OLS(d[y], sm.add_constant(d[cols])).fit(cov_type="HC3")

# ── 4. full-sample inventory beta ──
print("\n=== Inventory beta on WTI (full sample, REAL consensus) ===")
for y in ["wti_day", "wti_car2"]:
    m = fit(ev, y, ["surprise"]); mc = fit(ev, y, ["surprise", "dxy_day", "spx_day"])
    print(f"  {y:8s}  raw beta={m.params['surprise']:+.3f} (p={m.pvalues['surprise']:.3f}, R2={m.rsquared:.3f}) | "
          f"macro-controlled beta={mc.params['surprise']:+.3f} (p={mc.pvalues['surprise']:.3f}, R2={mc.rsquared:.3f})")

# ── 5. inventory beta BY REGIME ──
regimes = [
    ("2019 normal",       "2019-01-01", "2020-02-15"),
    ("COVID 2020",        "2020-02-15", "2020-12-31"),
    ("2021 recovery",     "2021-01-01", "2022-02-01"),
    ("Ukraine 2022",      "2022-02-01", "2022-12-31"),
    ("2023-24 normalize", "2023-01-01", "2025-01-01"),
    ("2025",              "2025-01-01", "2026-03-01"),
    ("2026 war regime",   "2026-03-01", "2026-12-31"),
]
print("\n=== Macro-controlled inventory beta BY REGIME (WTI day, REAL consensus) ===")
print(f"{'regime':20s} {'N':>4} {'beta':>8} {'p':>7} {'R2':>6}  reads")
for nm, a, b in regimes:
    d = ev[(ev.date >= a) & (ev.date < b)]
    if len(d) < 8:
        print(f"{nm:20s} {len(d):>4}  (too few)"); continue
    mc = fit(d, "wti_day", ["surprise", "dxy_day", "spx_day"])
    be, pv = mc.params["surprise"], mc.pvalues["surprise"]
    tag = "**inventory drove price**" if (pv < 0.05 and be < 0) else ("(right sign)" if be < 0 else "(wrong sign)")
    print(f"{nm:20s} {len(d):>4} {be:>+8.3f} {pv:>7.3f} {mc.rsquared:>6.3f}  {tag}")

# ── 6. CALM vs CRISIS contrast + interaction ──
crisis = [("2020-02-15", "2020-12-31"), ("2022-02-01", "2022-12-31"), ("2026-03-01", "2026-12-31")]
ev["crisis"] = 0
for a, b in crisis:
    ev.loc[(ev.date >= a) & (ev.date < b), "crisis"] = 1
print("\n=== CALM vs CRISIS (macro-controlled, REAL consensus) ===")
for nm, d in [("CALM (non-crisis)", ev[ev.crisis == 0]), ("CRISIS (COVID/Ukraine/war)", ev[ev.crisis == 1])]:
    mc = fit(d, "wti_day", ["surprise", "dxy_day", "spx_day"])
    print(f"  {nm:28s} N={len(d):>3}  beta={mc.params['surprise']:+.3f}  p={mc.pvalues['surprise']:.3f}")
ev["surp_x_crisis"] = ev["surprise"] * ev["crisis"]
mi = fit(ev, "wti_day", ["surprise", "surp_x_crisis", "dxy_day", "spx_day"])
print(f"  interaction: calm beta={mi.params['surprise']:+.3f} (p={mi.pvalues['surprise']:.3f}), "
      f"crisis shift={mi.params['surp_x_crisis']:+.3f} (p={mi.pvalues['surp_x_crisis']:.3f})")

# ── 7. rolling OOS skill ──
def rolling_oos(d, y, cols, start=104):
    d = d.reset_index(drop=True); pr = np.full(len(d), np.nan)
    for i in range(start, len(d)):
        m = sm.OLS(d[y].iloc[:i], sm.add_constant(d[cols].iloc[:i], has_constant="add")).fit()
        xi = d[cols].iloc[[i]].copy(); xi.insert(0, "const", 1.0); pr[i] = float(m.predict(xi).iloc[0])
    mask = ~np.isnan(pr); yy = d[y].values[mask]; pp = pr[mask]
    base = d[y].expanding().mean().shift().values[mask]
    return 1 - np.sum((yy - pp) ** 2) / np.sum((yy - base) ** 2), int(mask.sum())
oos, n = rolling_oos(ev, "wti_day", ["surprise"])
print(f"\nrolling OOS skill-R2 (inventory-only, full sample, N_test={n}): {oos:+.3f}")

# ── 8. proxy-vs-real cross check on the overlap (did the proxy hold up?) ──
print("\n(real surprise std this sample =", round(ev.surprise.std(), 2),
      "; proxy run was 3.32 -> real has more dispersion, less attenuation)")
