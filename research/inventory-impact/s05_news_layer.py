"""Step 4 - News layer

Build + execute rough_work/05_step4_news_layer.ipynb (Step 4).
GDELT oil-news INTENSITY as the news/geopolitical regime variable:
 - validate vs Brent volatility/timeline
 - #1 regime split: inventory beta on quiet vs loud news weeks (+ interaction)
 - conditional tomorrow read
Uses the cached GDELT pull (rough_work/cache/gdelt_oilvol_raw.json) so it runs
offline; to refresh, delete that file and re-pull (GDELT throttles ~1 req/60s).

Auto-extracted from _build_step4.py (was a notebook); run with the energy venv.
"""

# # Step 4 — **News / geopolitical amplifier layer (GDELT)**
#
# Our blind spot: the inventory signal was swamped by a geopolitical premium our
# market model (DXY/S&P, R²=0.28) couldn't see. **GDELT** oil-news **intensity**
# gives us an objective handle on that driver.
#
# **Source:** GDELT DOC 2.0 `TimelineVolRaw`, theme `ECON_OILPRICE`, English, Mar→now
# (free, keyless; throttles ~1 req/60s, so the pull is cached in
# `cache/gdelt_oilvol_raw.json`). Intensity = oil-article count ÷ total articles.
#
# **Validated:** intensity vs Brent realized-vol **+0.76**, and the highest-intensity
# days are the biggest move days (Apr-8 −14%, Mar-23 −12%) → a credible measure of
# "how dominant is the oil-news driver". **Caveat:** intensity tracks *magnitude*, not
# *direction* → it's a **regime/conditioning** variable (#1), not a directional control.
#
# **This step:** split the 16 releases into **quiet vs loud** news weeks and compare the
# inventory beta — does the (weak) signal break through when the tape is quiet?

# ## 0. Setup — GDELT intensity (cached) + event frame + abnormal return

import warnings, json; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm, yfinance as yf
import matplotlib.pyplot as plt
ROOT  = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
CACHE = ROOT / "research/inventory-impact/cache"
pd.set_option("display.width", 200, "display.float_format", lambda x: f"{x:,.3f}")

# --- GDELT intensity (from cache) ---
j = json.loads((CACHE/"gdelt_oilvol_raw.json").read_text())
g = pd.DataFrame(j["timeline"][0]["data"])
g["date"] = pd.to_datetime(g["date"].str[:8])
g["intensity"] = g["value"]/g["norm"]*1e4          # oil articles per 10k total coverage
g = g.set_index("date")[["value","intensity"]]
g = g[g.index <= "2026-06-23"]                      # drop partial 24-Jun

# --- daily macro + abnormal return (Step-1 redo) ---
def dc(s):
    x = yf.download(s, period="6mo", interval="1d", progress=False, auto_adjust=False)["Close"][s].dropna()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px  = pd.concat({"brent":dc("BZ=F"),"dxy":dc("DX-Y.NYB"),"spx":dc("^GSPC")},axis=1).dropna()
ret = np.log(px).diff().dropna(); ret = ret[ret.index>="2026-03-01"]
ret["abn"] = sm.OLS(ret["brent"], sm.add_constant(ret[["dxy","spx"]])).fit().resid

# pre-release news backdrop = mean intensity over the 5 days BEFORE the release (exclude release day)
backdrop = g["intensity"].rolling(5).mean().shift(1)

ev = pd.read_parquet(CACHE/"event_table.parquet")
ev["date"] = ev["release"].dt.tz_convert(None).dt.normalize()
ev = ev.merge((ret["abn"]*100).rename("abn_daily"), left_on="date", right_index=True, how="left")
ev = ev.merge(backdrop.rename("news_bd"),           left_on="date", right_index=True, how="left")
d = ev.dropna(subset=["crude_surp","abn_daily","news_bd"]).sort_values("release").reset_index(drop=True)
print("events with news backdrop:", len(d))
print(d[["release","crude_surp","abn_daily","news_bd"]].round(2).to_string(index=False))


# ## 1. Validation recap — intensity tracks volatility, not direction

chk = pd.DataFrame({"intensity":g["intensity"]}).join(np.log(px["brent"]).diff().rename("ret"), how="inner").dropna()
chk["absret"] = chk["ret"].abs()*100
chk["rvol10"] = chk["ret"].rolling(10).std()*100
print(f"corr(intensity, |ret|)  = {chk['intensity'].corr(chk['absret']):+.2f}")
print(f"corr(intensity, rvol10) = {chk['intensity'].corr(chk['rvol10'].bfill()):+.2f}")
print(f"intensity: Apr run-up mean = {g.loc['2026-04','value'].mean():.0f}  vs  Jun mean = {g.loc['2026-06','value'].mean():.0f}")


# ## 2. #1 — Regime split: does inventory bite on QUIET news weeks?
#
# Split the releases at the median pre-release news backdrop. Hypothesis: |inventory
# beta| larger / more negative on **quiet** weeks; ≈0 on **loud** weeks (overridden).

thr = d["news_bd"].median()
lo = d[d["news_bd"] <  thr]; hi = d[d["news_bd"] >= thr]
def beta(sub):
    m = sm.OLS(sub["abn_daily"], sm.add_constant(sub["crude_surp"])).fit()
    return m.params["crude_surp"], m.pvalues["crude_surp"], m.rsquared, len(sub)
for name, sub in [("ALL", d), (f"QUIET news (bd<{thr:.0f})", lo), (f"LOUD news (bd>={thr:.0f})", hi)]:
    b,p,r2,n = beta(sub)
    print(f"  {name:24s} n={n:2d}  inv-beta={b:+.3f}  p={p:.2f}  R2={r2:.2f}")
print("\n(>0 -> wrong sign; expect more-negative & lower-p in QUIET bucket if the hypothesis holds)")

# interaction (uses all 16): abn ~ surprise + intensity_z + surprise*intensity_z
d2 = d.copy(); d2["iz"] = (d2["news_bd"]-d2["news_bd"].mean())/d2["news_bd"].std()
d2["surp_x_iz"] = d2["crude_surp"]*d2["iz"]
mi = sm.OLS(d2["abn_daily"], sm.add_constant(d2[["crude_surp","iz","surp_x_iz"]])).fit(cov_type="HC3")
print("\nInteraction model (N=16):")
print(pd.DataFrame({"coef":mi.params,"p":mi.pvalues}).round(3).to_string())
print("  interpret: surp_x_iz > 0 => louder news pushes the (negative) inventory beta toward 0 (overridden).")


# ## 3. Conditional read for tomorrow

cur = g["intensity"].rolling(5).mean().iloc[-1]
pct = (g["intensity"].rolling(5).mean() <= cur).mean()*100
b_lo,p_lo,_,n_lo = beta(lo); b_hi,p_hi,_,n_hi = beta(hi)
tape = "QUIET" if cur < thr else "LOUD"
print(f"current 5d news backdrop = {cur:.0f}  ({pct:.0f}th pct of the window)  ->  tape looks {tape}")
print(f"  quiet-week inv-beta {b_lo:+.2f} (n={n_lo})   loud-week inv-beta {b_hi:+.2f} (n={n_hi})")
print(f"\nApplied beta for tomorrow ~ {b_lo if tape=='QUIET' else b_hi:+.2f} %/Mbbl")
print("Scenario (beta x surprise vs -5.1 consensus):")
use = b_lo if tape=="QUIET" else b_hi
for a in [-9,-7,-5.1,-3,1]:
    s=a-(-5.1); print(f"  actual {a:+5.1f} -> surprise {s:+4.1f} -> {use*s:+.2f}% Brent")


# ## 4. Read-through — the honest result of the conditioning
#
# **GDELT delivered a *validated* regime variable.** Intensity vs Brent realized-vol
# = **+0.70**, and it spikes on the −14% / −12% crash days. So factor #1 (the
# geopolitical/news regime) is now **measured**, not eyeballed off the price path — a
# genuinely useful, reusable gauge for the dashboard.
#
# **But conditioning did NOT rescue the inventory signal — this is a null.**
# - QUIET-news weeks (n=7): inv-beta **−0.09, p=0.88** → essentially zero
# - LOUD-news weeks (n=8): inv-beta **−0.29, p=0.67** → right sign, still insignificant
# - Interaction `surp×intensity`: **p=0.73** → noise
# This is the *opposite* of the hypothesis (we expected QUIET weeks to show the stronger
# signal), and every estimate is statistical noise. **There is no detectable news regime
# in which the inventory print reliably moves Brent** in this window.
#
# **Why we can't conclude more (a real confound):** news intensity fell ~monotonically
# over March→now (≈155 → ≈50), so **"quiet" ≈ "recent."** The split is entangled with the
# calendar/regime evolution and, at N=15 with ~7–8 per bucket, is **underpowered by
# construction**. We genuinely cannot separate "quiet news" from "later period" here.
#
# **Effect on the call: unchanged — NEUTRAL, if anything more firmly.** The current tape
# *is* quiet (≈9th percentile), but quiet weeks showed ~zero inventory sensitivity, so a
# quiet backdrop does **not** argue for trusting the print more. GDELT sharpened our
# *measurement* of the regime and confirmed factor #1's dominance; it did **not** surface
# a hidden inventory edge — consistent end-to-end with the Step-3 OOS null.
#
# **Net contribution of Step 4:** (a) an objective, validated geopolitical-regime gauge
# (reusable dashboard asset), and (b) confirmation that even regime-conditioning can't
# extract inventory predictive power at this N/regime — not a signal we missed.
#
# **Long-term (parked):** the full GDELT headline-impact engine (2017+ history, factor
# classification, scheduled-event tagging) as a reusable dashboard capability.
