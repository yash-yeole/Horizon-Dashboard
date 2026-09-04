"""Step 8 - WTI forecast + product reactions

Build + execute rough_work/08_wti_forecast_and_reaction.ipynb (Step 7 / final).

Consolidates the WTI pivot: predict the EIA crude number from fundamentals, then
predict the market reaction. Sections:
  1. Predict the number  (supply/demand balance model; equation, train/test, OOS,
     24-Jun backtest vs the Reuters consensus)
  2. Reaction model + factor audit  (WTI ~ surprise + DXY + S&P; all other
     discussed factors tested and rejected)
  3. Product reactions  (RBOB/HO react to their OWN surprise; the cracks)
  4. Long-history regime finding  (inventories only drove WTI in 2019)
  5. The deliverable

Run with the energy venv (kernel 'energy'). Reuses WTI_consensus.csv + EIA API.

Auto-extracted from _build_step8.py (was a notebook); run with the energy venv.
"""

# # Step 7 — **Predict the number, then the reaction (WTI)**
#
# Two corrections lock the framework in the right direction:
# - **WTI, not Brent** — EIA measures *US* crude, so the US barrel responds.
# - **Consensus, not API** — anchor surprises on the published Reuters consensus
#   (`WTI_consensus.csv`, 2019-2026), the number the market actually trades against.
#
# And a shift in task: instead of only *reacting* to the print, we **forecast the
# number ourselves** from fundamentals, then map our surprise to the reaction, then
# score it. This notebook is the consolidated, productionized framework
# (`backend/app/services/inventory_forecast.py` + `release_impact.py`).

# ## 0. Setup

import warnings, math, json; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, httpx, yfinance as yf, statsmodels.api as sm
ROOT = Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard")
pd.set_option("display.width", 200, "display.float_format", lambda x: f"{x:,.3f}")
def eia_key():
    for ln in (ROOT/"backend/.env").read_text().splitlines():
        if ln.startswith("HORIZON_EIA_API_KEY="): return ln.split("=",1)[1].strip()
KEY = eia_key()
def eia(sid, length=560):
    j = httpx.Client(timeout=40).get(f"https://api.eia.gov/v2/seriesid/{sid}",
        params={"api_key":KEY,"length":length}).json()["response"]["data"]
    s = pd.DataFrame(j)[["period","value"]]; s["period"]=pd.to_datetime(s["period"]); s["value"]=pd.to_numeric(s["value"])
    return s.sort_values("period").set_index("period")["value"]
print("EIA key:", bool(KEY))


# ## 1. Predict the number — the supply/demand balance model
#
# `dStock_t ~ balance(t-1) + dSPR(t-1) + AR(1,2) + seasonality`, where
# `balance = (production + imports - exports - refinery_inputs)*7`. Everything is
# **lag-1** so it is genuinely known before the Wednesday release.

stocks=eia("PET.WCESTUS1.W"); prod=eia("PET.WCRFPUS2.W"); imp=eia("PET.WCEIMUS2.W")
exp=eia("PET.WCREXUS2.W"); refin=eia("PET.WCRRIUS2.W"); spr=eia("PET.WCSSTUS1.W")
df=pd.DataFrame({"stocks":stocks,"prod":prod,"imp":imp,"exp":exp,"refin":refin,"spr":spr}).dropna()
df["dstock"]=df["stocks"].diff()/1000; df["bal"]=(df["prod"]+df["imp"]-df["exp"]-df["refin"])*7/1000; df["dspr"]=df["spr"].diff()/1000
woy=df.index.isocalendar().week.astype(float).values
X=pd.DataFrame(index=df.index); X["const"]=1.0
X["bal_l1"]=df["bal"].shift(1); X["dspr_l1"]=df["dspr"].shift(1); X["ar1"]=df["dstock"].shift(1); X["ar2"]=df["dstock"].shift(2)
for h in (1,2): X[f"sin{h}"]=np.sin(2*np.pi*h*woy/52); X[f"cos{h}"]=np.cos(2*np.pi*h*woy/52)
COLS=[c for c in X.columns if c!="const"]; data=X.join(df["dstock"]).dropna()
print(f"weekly obs: {len(data)}  {data.index.min().date()} -> {data.index.max().date()}")


# ### The equation (full-sample fit) + t-stats

full=sm.OLS(data["dstock"],data[["const"]+COLS]).fit(cov_type="HC3")
print(f"dStock = {full.params['const']:+.3f}")
for c in COLS:
    st="***" if full.pvalues[c]<.01 else "**" if full.pvalues[c]<.05 else "*" if full.pvalues[c]<.1 else ""
    print(f"        {full.params[c]:+.3f} * {c:8s}  t={full.tvalues[c]:+5.2f}  p={full.pvalues[c]:.3f} {st}")
print(f"in-sample R2={full.rsquared:.3f}")


# ### Validation — fixed 70/30 hold-out + expanding walk-forward

def stats(a,p):
    e=a-p; return np.sqrt((e**2).mean()), 1-(e**2).sum()/((a-a.mean())**2).sum(), (np.sign(a)==np.sign(p)).mean()
cut=int(len(data)*0.7); tr,te=data.iloc[:cut],data.iloc[cut:]
m_tr=sm.OLS(tr["dstock"],tr[["const"]+COLS]).fit()
pte=m_tr.predict(te[["const"]+COLS]); rmse_te,r2_te,hit_te=stats(te["dstock"],pte)
print(f"70/30 split: train {len(tr)} -> test {len(te)} | train R2={m_tr.rsquared:.3f}  TEST R2={r2_te:+.3f}  hit={hit_te:.1%}")
pred=np.full(len(data),np.nan)
for i in range(156,len(data)):
    mm=sm.OLS(data["dstock"].iloc[:i],data[["const"]+COLS].iloc[:i]).fit()
    pred[i]=float(mm.predict(data[["const"]+COLS].iloc[[i]]).iloc[0])
oos=data.assign(p=pred).dropna(subset=["p"]); _,r2_oos,hit_oos=stats(oos["dstock"],oos["p"])
print(f"walk-forward OOS (N={len(oos)}): R2={r2_oos:+.3f}  hit={hit_oos:.1%}")


# ### The 24-Jun-2026 print, scored vs the consensus (model never saw the actual)

target=data.index.max(); trn=data[data.index<target]
om=sm.OLS(trn["dstock"],trn[["const"]+COLS]).fit()
ours=float(om.predict(data[["const"]+COLS].loc[[target]]).iloc[0]); actual=float(data["dstock"].loc[target])
cons=pd.read_csv(ROOT/"research/inventory-impact/WTI_consensus.csv")
cons["Actual"]=pd.to_numeric(cons["Actual"].astype(str).str.replace("M",""),errors="coerce")
cons["Forecast"]=pd.to_numeric(cons["Forecast"].astype(str).str.replace("M",""),errors="coerce")
c2406=float(cons.iloc[0]["Forecast"])
print(f"OUR forecast   : {ours:+.2f} M bbl")
print(f"Reuters cons.  : {c2406:+.2f} M bbl")
print(f"ACTUAL (EIA)   : {actual:+.2f} M bbl")
print(f"our error {actual-ours:+.2f}  vs consensus error {actual-c2406:+.2f}  -> "
      f"{'OUR MODEL closer' if abs(actual-ours)<abs(actual-c2406) else 'consensus closer'}")


# ## 2. Reaction model + factor audit
#
# The WTI reaction spec is `wti_day ~ surprise + DXY + S&P`. We test every other
# factor we discussed (vol, product surprises, news tone, backwardation) — none is
# significant and none changes the (already small) inventory beta.

cons["rel"]=pd.to_datetime(cons["Release date"],format="%d-%m-%Y").dt.normalize()
cons["crude_surp"]=cons["Actual"]-cons["Forecast"]; C=cons.dropna(subset=["crude_surp"]).sort_values("rel")
def dc(s):
    x=yf.download(s,period="8y",interval="1d",progress=False,auto_adjust=False)["Close"][s].dropna()
    x.index=pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px=pd.concat({"wti":dc("CL=F"),"dxy":dc("DX-Y.NYB"),"spx":dc("^GSPC")},axis=1).dropna()
ret=np.log(px).diff()*100; rvol=ret["wti"].rolling(20).std()
def onrel(r,s):
    f=s.index[s.index>=r]; return float(s.loc[f[0]]) if len(f) else np.nan
for nm,s in [("wti_day",ret["wti"]),("dxy_day",ret["dxy"]),("spx_day",ret["spx"]),("rvol",rvol.shift(1))]:
    C[nm]=C["rel"].map(lambda r: onrel(r,s))
ev=C.dropna(subset=["wti_day","crude_surp"]).reset_index(drop=True)
def eqn(d,y,cols,title):
    d=d.dropna(subset=[y]+cols); m=sm.OLS(d[y],sm.add_constant(d[cols])).fit(cov_type="HC3")
    print(f"{title} (N={len(d)},R2={m.rsquared:.3f}): "+"  ".join(f"{c}={m.params[c]:+.3f}(p{m.pvalues[c]:.2f})" for c in cols))
eqn(ev,"wti_day",["crude_surp","dxy_day","spx_day"],"CURRENT SPEC")
eqn(ev,"wti_day",["crude_surp","dxy_day","spx_day","rvol"],"+ realized vol")
print("(news Delta-tone & backwardation tested war-regime-only -> also insignificant; see _wti_reaction_full.py)")


# ## 3. Product reactions — RBOB & distillate
#
# Products react to their **own** stock surprise (and the cracks isolate it), where
# crude flat price does not. Product surprises use the model-expected baseline
# (no free product consensus); the crude surprise is the real consensus.

def expsurp(chg,min_train=104):
    woy=chg.index.isocalendar().week.astype(float).values
    Z=pd.DataFrame(index=chg.index); Z["const"]=1.0
    for h in (1,2): Z[f"sin{h}"]=np.sin(2*np.pi*h*woy/52); Z[f"cos{h}"]=np.cos(2*np.pi*h*woy/52)
    for L in (1,2,3,4): Z[f"lag{L}"]=chg.shift(L).values
    pr=np.full(len(chg),np.nan)
    for i in range(len(chg)):
        xi=Z.iloc[[i]]
        if i<min_train or xi.isna().any().any(): continue
        t=Z.iloc[:i].dropna()
        if len(t)<60: continue
        pr[i]=float(sm.OLS(chg.loc[t.index],t).fit().predict(xi).iloc[0])
    return chg-pd.Series(pr,index=chg.index)
gas=expsurp((eia("PET.WGTSTUS1.W").diff()/1000).dropna()); dist=expsurp((eia("PET.WDISTUS1.W").diff()/1000).dropna())
C["week_end"]=(C["rel"]-pd.Timedelta(days=5)).dt.normalize()
def near(s,w):
    p=s.index.get_indexer([w],method="nearest")[0]; return s.iloc[p] if abs((s.index[p]-w).days)<=4 else np.nan
C["gas_surp"]=C["week_end"].map(lambda w: near(gas,w)); C["dist_surp"]=C["week_end"].map(lambda w: near(dist,w))
rb=dc("RB=F"); ho=dc("HO=F"); pr2=pd.concat({"rb":rb,"ho":ho},axis=1).reindex(px.index)
rr=np.log(pr2).diff()*100
for nm,s in [("rb_ret",rr["rb"]),("ho_ret",rr["ho"])]: C[nm]=C["rel"].map(lambda r: onrel(r,s))
e=C.dropna(subset=["rb_ret","crude_surp"]).reset_index(drop=True)
eqn(e,"rb_ret",["gas_surp","crude_surp"],"RBOB ~ gasoline surp")
eqn(e.dropna(subset=["ho_ret"]),"ho_ret",["dist_surp","crude_surp"],"HO   ~ distillate surp")
print("=> products trade their OWN numbers; crude_surp insignificant for both.")


# ## 4. Long-history regime finding (2019-2026)
#
# Inventories reliably moved WTI **only in 2019**; since 2020 the print is a
# non-driver on a daily basis (COVID, Ukraine, the 2026 war all swamp it).

def fit(d,y,cols): return sm.OLS(d[y],sm.add_constant(d[cols])).fit(cov_type="HC3")
for nm,a,b in [("2019",  "2019-01-01","2020-02-15"),("COVID 2020","2020-02-15","2020-12-31"),
               ("2021-22","2021-01-01","2022-12-31"),("2023-24","2023-01-01","2025-01-01"),
               ("2025-26","2025-01-01","2026-12-31")]:
    d=ev[(ev.rel>=a)&(ev.rel<b)]
    if len(d)<8: continue
    m=fit(d,"wti_day",["crude_surp","dxy_day","spx_day"])
    print(f"{nm:9s} N={len(d):>3} beta={m.params['crude_surp']:+.3f} p={m.pvalues['crude_surp']:.3f}")


# ## 5. The deliverable (24-Jun-2026)
#
# - **Bias: NEUTRAL** (slight bullish tilt) — our forecast is a bigger draw than
#   consensus, but the WTI inventory beta is small/insignificant in this regime; the
#   dollar, risk and geopolitical news dominate.
# - **Products/spreads:** WTI flat ~neutral; the **RBOB-WTI and HO-WTI cracks** are
#   the most inventory-sensitive vehicles, with a mild bearish lean on our forecast
#   product builds.
# - **Top-3 factors:** (1) our forecast surprise vs consensus, (2) the dollar/macro
#   regime (DXY), (3) the geopolitical-news tape — which net to NEUTRAL.
# - **Framework:** predict the number (balance + seasonality + momentum, OOS R2~0.11,
#   beat the consensus on 24-Jun) -> surprise vs consensus -> regime-conditional WTI
#   reaction -> spread routing. Productionized in `inventory_forecast.py` +
#   `release_impact.py` and shipped to the dashboard.
