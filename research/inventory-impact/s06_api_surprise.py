"""Step 5 - API surprise layer

Build + execute rough_work/06_step5_api_surprise.ipynb (Step 5).
The API-refined surprise: replace EIA-consensus with EIA-API as the surprise
baseline (the market's UPDATED expectation by Wednesday). Documents the win
(intraday) and the pooling null. Uses cached API pull. Run with the energy venv.

Auto-extracted from _build_step5.py (was a notebook); run with the energy venv.
"""

# # Step 5 — **The API-refined surprise** (the one real improvement)
#
# By Wednesday 10:30 ET the market has already seen **API** (Tuesday 4:30pm ET) and
# repriced. So the genuinely *new* information in the EIA print is **`EIA − API`**, not
# `EIA − consensus` (which is stale — set before API existed). We've been measuring the
# surprise against the wrong baseline.
#
# **Result:** on the clean intraday +2h window, swapping the baseline lifts the model
# from *no signal* to the **first positive out-of-sample skill** in the whole project —
# fixing a measurement flaw, not adding a parameter.
#
# Source: Investing.com event **656** "API Weekly Crude Oil Stock" (free, keyless).

# ## 0. Setup — event table, abnormal return, API history

import warnings, json, re; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, httpx, statsmodels.api as sm, yfinance as yf
import matplotlib.pyplot as plt
ROOT=Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard"); CACHE=ROOT/"research/inventory-impact/cache"
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
pd.set_option("display.width",200,"display.float_format",lambda x:f"{x:,.3f}")
ev=pd.read_parquet(CACHE/"event_table.parquet"); ev["date"]=ev["release"].dt.tz_convert(None).dt.normalize()
def dc(s):
    x=yf.download(s,period="6mo",interval="1d",progress=False,auto_adjust=False)["Close"][s].dropna()
    x.index=pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px=pd.concat({"brent":dc("BZ=F"),"dxy":dc("DX-Y.NYB"),"spx":dc("^GSPC")},axis=1).dropna()
ret=np.log(px).diff().dropna(); ret=ret[ret.index>="2026-03-01"]
ret["abn"]=sm.OLS(ret["brent"],sm.add_constant(ret[["dxy","spx"]])).fit().resid*100
ev=ev.merge(ret["abn"].rename("abn_daily"),left_on="date",right_index=True,how="left")
# API (event 656), cached
apath=CACHE/"api_weekly_656.json"
if apath.exists(): occ=json.loads(apath.read_text())
else:
    h=httpx.get("https://www.investing.com/economic-calendar/api-weekly-crude-oil-stock-656",headers=UA,timeout=25,follow_redirects=True).text
    occ=json.loads(re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',h,re.S).group(1))["props"]["pageProps"]["state"]["economicCalendarEventStore"]["occurrences"]
    apath.write_text(json.dumps(occ))
api=pd.DataFrame([{"t":pd.to_datetime(o["occurrence_time"],utc=True),"api":o.get("actual"),"api_fc":o.get("forecast")} for o in occ]).dropna(subset=["t","api"]).sort_values("t")
def api_for(rel,col):
    w=api[(api["t"]<=rel)&(api["t"]>=rel-pd.Timedelta(days=2))]; return w[col].iloc[-1] if len(w) else np.nan
ev["api"]=ev["release"].map(lambda r: api_for(r,"api")); ev["api_fc"]=ev["release"].map(lambda r: api_for(r,"api_fc"))
d=ev.dropna(subset=["crude_actual","api","ret_2h_%"]).reset_index(drop=True)
d["s_cons"]=d["crude_surp"]; d["s_api"]=d["crude_actual"]-d["api"]; d["s_bld"]=d["crude_actual"]-0.5*(d["crude_fc"]+d["api"])
print("events:",len(d)); print(d[["date","crude_actual","crude_fc","api","s_cons","s_api"]].round(2).to_string(index=False))


# ## 1. Surprise baseline comparison (intraday +2h is the clean test — API already priced)

def loocv(df,cols,y="ret_2h_%"):
    df=df.reset_index(drop=True); yy=df[y]; n=len(df); pr=np.full(n,np.nan)
    for i in range(n):
        tr=[j for j in range(n) if j!=i]
        m=sm.OLS(yy.iloc[tr],sm.add_constant(df.loc[tr,cols],has_constant='add')).fit()
        xi=df.loc[[i],cols].copy(); xi.insert(0,"const",1.0); pr[i]=float(m.predict(xi).iloc[0])
    base=np.array([yy.iloc[[j for j in range(n) if j!=i]].mean() for i in range(n)])
    return 1-np.sum((yy.values-pr)**2)/np.sum((yy.values-base)**2)
for tgt in ["ret_2h_%","abn_daily"]:
    print(f"\n--- target: {tgt} ---")
    for nm,c in [("EIA-consensus","s_cons"),("EIA-API","s_api"),("EIA-blend","s_bld")]:
        m=sm.OLS(d[tgt],sm.add_constant(d[c])).fit()
        print(f"  {nm:13s} beta={m.params[c]:+.3f} p={m.pvalues[c]:.2f} R2={m.rsquared:.3f} OOS={loocv(d,[c],tgt):+.3f}")


# **Read:** on `ret_2h` (post-10:30, API already priced) `EIA−API` jumps R² 0.01→0.12 and
# crosses to **positive OOS (+0.04)** — vs negative for consensus. On `abn_daily` it *hurts*,
# because the daily window double-counts the Tuesday-night API move. The model improving
# exactly where theory says it should (and breaking where it shouldn't) is the credibility check.

# ## 2. Pooling experiment — API as its own event (honest null)

# API's own event: surprise = API-forecast, reaction = +2h after Tue ~20:30Z
lco=pd.read_parquet(CACHE/"lco_c1.parquet")["mid"]; lco_last=lco.index.max()
bz=yf.download("BZ=F",period="60d",interval="15m",progress=False,auto_adjust=False)["Close"]["BZ=F"].dropna(); bz.index=pd.to_datetime(bz.index).tz_convert("UTC")
def react(t0,hrs=2):
    s=(lco if t0<=lco_last else bz).dropna(); p0=s.asof(t0); p1=s.asof(t0+pd.Timedelta(hours=hrs))
    return 100*np.log(p1/p0) if (p0 and p1 and p0>0 and p1>0) else np.nan
ap=api[(api["t"]>="2026-03-01")&(api["t"]<="2026-06-20")].copy(); ap["surprise"]=ap["api"]-ap["api_fc"]
ap["reaction"]=ap["t"].map(react); ap=ap.dropna(subset=["surprise","reaction"])
eia=d.rename(columns={"s_cons":"surprise","ret_2h_%":"reaction"})[["surprise","reaction"]].assign(source="EIA")
apiev=ap[["surprise","reaction"]].assign(source="API")
pool=pd.concat([eia,apiev],ignore_index=True); pool["is_api"]=(pool["source"]=="API").astype(int)
for nm,sub,cols in [("EIA only (N=16)",eia,["surprise"]),("API only",apiev,["surprise"]),
                    ("POOLED",pool,["surprise"]),("POOLED+dummy",pool,["surprise","is_api"])]:
    m=sm.OLS(sub["reaction"],sm.add_constant(sub[cols])).fit()
    print(f"  {nm:16s} N={len(sub)} R2={m.rsquared:.3f} beta_surp={m.params['surprise']:+.3f} (p={m.pvalues['surprise']:.2f})")
print("\nNULL: EIA beta (+) and API beta (-) have OPPOSITE signs -> pooling cancels them.")
print("API window lands near the ICE close (~22:00Z) so its reaction is thin (smaller variance).")


# ## 3. The current best equation + tomorrow's call

best=sm.OLS(d["ret_2h_%"],sm.add_constant(d["s_api"])).fit()
a,b=best.params["const"],best.params["s_api"]
print(f"BEST inventory spec:  ret_2h(+2h) = {a:+.3f} + {b:+.3f} * (EIA - API)   [R2={best.rsquared:.2f}, p={best.pvalues['s_api']:.2f}, OOS=+0.04]")
print("  (sign is counterintuitive & unstable at N=16 -> informative, not yet tradeable)\n")
CONS, API_TUE = -5.1, -0.765   # 24-Jun consensus / 23-Jun API
print(f"TOMORROW: consensus {CONS} vs API {API_TUE} -> expectations UNANCHORED (gap {CONS-API_TUE:+.1f}M)")
print("Surprise by baseline if EIA prints:")
for x in [-9,-7,-5,-3,-1]:
    print(f"  EIA {x:+.1f}:  vs consensus={x-CONS:+.1f}   vs API={x-API_TUE:+.1f}  (market repriced toward API)")


# ## 4. Read-through
#
# - **The win:** `EIA−API` is the one change that improved out-of-sample skill (−0.17 → +0.04
#   on the intraday window) — and it *subsumes* the old consensus surprise (which collapses to
#   ~0 once `EIA−API` is in). Your API insight gave the project its only real lift. It works
#   because it **fixes the surprise's baseline**, not because it adds a factor.
# - **The null:** pooling API+EIA into ~30 events did **not** break the N wall — the two prints'
#   reactions point in opposite (insignificant) directions, so they cancel. More data didn't help
#   because the signal is genuinely weak/inconsistent in this regime.
# - **Still honest:** even the best spec is **p≈0.18, OOS +0.04** — *suggestive, not significant*,
#   with an unstable sign. The call stays **NEUTRAL**; the inventory print is a secondary driver.
# - **Tomorrow's practical edge:** consensus (−5.1) and API (−0.77) diverge hugely, so expectations
#   are unanchored. The market likely sits near API's small draw, so a *solid* EIA draw (−5 to −7) —
#   "in-line" vs the stale consensus — would actually be an **upside surprise vs what's now priced.**
#
# **Note on news / GDELT (see notebook 05):** GDELT is used only as a *news-intensity regime gauge*
# (volume, not sentiment); its split was null. News is not currently a model input beyond that — the
# binding constraints are N and the geopolitical regime, which a better news model wouldn't fix here
# (though a directional geopolitical factor would be the long-term #3 engine).
