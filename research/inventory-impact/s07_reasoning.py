"""Step 6 - Reasoning layer

Build + execute rough_work/07_reasoning_layer.ipynb (Step 6 / reasoning).
Turns the model into the DELIVERABLE's reasoning: a quantified driver ranking
(top-3 factors, news included), a headline-driven narrative (RSS), and
theme->spread routing. Uses cached GDELT tone + cached RSS headlines.

Auto-extracted from _build_step6_reasoning.py (was a notebook); run with the energy venv.
"""

# # Step 6 — **Reasoning layer: top-3 factors, narrative, spread routing**
#
# News can't *predict* the inventory print (contemporaneous + orthogonal), but it's
# central to the **other** deliverables. This step turns the model into the
# assignment's reasoning:
# 1. **Quantified driver ranking** → the empirical "top-3 factors" (news now included).
# 2. **Headline narrative** (FinancialJuice/OilPrice RSS) → *why*, in plain words.
# 3. **Theme → spread routing** → which product is topical right now.

# ## 0. Setup — daily war-regime model (DXY, S&P, news Δtone) + headlines

import warnings, json, re; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
ROOT=Path(r"C:/Users/yash.yeole/OneDrive - hertshtengroup.com/Documents/energy-dashboard"); CACHE=ROOT/"research/inventory-impact/cache"
pd.set_option("display.width",200,"display.float_format",lambda x:f"{x:,.3f}")
tone=pd.DataFrame(json.loads((CACHE/"gdelt_oiltone.json").read_text())["timeline"][0]["data"])
tone["date"]=pd.to_datetime(tone["date"].str[:8]); dtone=tone.set_index("date")["value"].diff().rename("dtone")
def dc(s):
    x=yf.download(s,period="2y",interval="1d",progress=False,auto_adjust=False)["Close"][s].dropna()
    x.index=pd.to_datetime(x.index).tz_localize(None).normalize(); return x
px=pd.concat({"brent":dc("BZ=F"),"dxy":dc("DX-Y.NYB"),"spx":dc("^GSPC")},axis=1).dropna()
ret=np.log(px).diff().dropna().join(dtone,how="inner").dropna()
war=ret[ret.index>="2026-03-01"]
print(f"war-regime daily obs: {len(war)}  {war.index.min().date()} -> {war.index.max().date()}")
heads=json.loads((CACHE/"news_headlines_recent.json").read_text())
print(f"recent oil headlines cached: {len(heads)}")


# ## 1. Quantified driver ranking → the top-3 factors

X=war[["dxy","spx","dtone"]]; y=war["brent"]
m=sm.OLS(y,sm.add_constant(X)).fit(cov_type="HC3")
rows=[]
for c in X.columns:
    std_beta=m.params[c]*X[c].std()/y.std()
    incr=m.rsquared-sm.OLS(y,sm.add_constant(X.drop(columns=[c]))).fit().rsquared
    rows.append({"factor":c,"coef":m.params[c],"p":m.pvalues[c],"std_beta":std_beta,"incr_R2":incr})
rank=pd.DataFrame(rows).reindex(columns=["factor","coef","p","std_beta","incr_R2"])
rank["abs"]=rank["std_beta"].abs(); rank=rank.sort_values("abs",ascending=False).drop(columns="abs").reset_index(drop=True)
print(f"Daily Brent drivers (war regime), full model R2={m.rsquared:.3f}:\n")
print(rank.to_string(index=False))
print("\n+ inventory surprise: event-level (N=16), insignificant (p~0.2-0.3) -> ranks BELOW all daily factors.")
labels={"dtone":"News / geopolitical sentiment","dxy":"US dollar (DXY)","spx":"Equities / risk (S&P)"}
print("\n>>> TOP-3 FACTORS (by standardized impact):")
for i,r in rank.iterrows(): print(f"   {i+1}. {labels[r['factor']]:32s} std-beta {r['std_beta']:+.2f}  (p={r['p']:.2f})")


# ## 2. Headline narrative — what's actually driving the tape (RSS)

h=pd.DataFrame(heads).sort_values("date",ascending=False)
print("Most recent oil-relevant headlines:\n")
for _,x in h.head(10).iterrows(): print(f"  [{x['src'][:12]:12s}] {str(x['date'])[:16]}  {x['title'][:92]}")
# theme tally for the narrative + spread routing
cats={"Crude / geopolitics (Hormuz, Iran, OPEC, SPR, inventories)":r"crude|hormuz|iran|opec|supply|spr|inventor|tanker|barrel",
      "Gasoline / pump politics":r"gasoline|pump|rbob",
      "Distillate / diesel":r"diesel|distillate|heating|gasoil",
      "Demand / macro":r"demand|recession|growth|rate|economy"}
print("\nTheme tally (recent headlines):")
tally={k:int(h['title'].str.contains(v,case=False,regex=True).sum()) for k,v in cats.items()}
for k,v in sorted(tally.items(),key=lambda x:-x[1]): print(f"  {v:2d}  {k}")


# ## 3. Theme → spread routing (which product is topical)

route={"Crude / geopolitics (Hormuz, Iran, OPEC, SPR, inventories)":"flat Brent + WTI-Brent (US-crude / global-supply)",
       "Gasoline / pump politics":"gasoline crack (RBOB-Brent)",
       "Distillate / diesel":"distillate/gas-oil crack",
       "Demand / macro":"flat price (whole complex)"}
top=max(tally,key=tally.get)
print("Most topical theme right now:",top.split('(')[0].strip())
print("=> spread most likely in focus:",route[top])
print("\n(empirical spread betas from Step 2: WTI-Brent was the most surprise-sensitive of the complex,")
print(" |corr| 0.29 vs flat Brent 0.08 -- but none statistically reliable in this regime.)")


# ## 4. The consolidated deliverable
#
# **Bias: NEUTRAL on the print** — bearish-leaning *backdrop*. The tape is being driven by
# **Hormuz de-escalation** (US-Iran hotline to reopen the strait; "how much Iranian oil
# returns") and **political pressure for lower prices** (Trump/DOJ) — i.e. the war premium
# *unwinding* (Brent ~$76, −35% off the April peak). A weekly inventory print won't reverse
# that. The consensus (−5.1) vs API (−0.77) gap means expectations are unanchored, so only an
# *extreme* EIA number registers; the asymmetric risk is a surprise **build** compounding the
# selloff.
#
# **Products/spreads most likely affected:** **WTI–Brent** (US-specific crude print; the most
# surprise-sensitive spread we measured) > flat Brent; the gas-oil/distillate crack ~nil.
# Current headline themes skew **crude/geopolitical**, so attention routes to flat Brent +
# WTI–Brent, not the product cracks.
#
# **Top-3 factors (empirically ranked by standardized impact, war regime):**
# 1. **US dollar (DXY)** — top measured driver (std-β +0.38, p=0.003); Brent & USD co-moved as
#    war hedges — itself a geopolitical-regime signature.
# 2. **News / geopolitical sentiment (Δtone)** — close #2 (std-β −0.28, **p<0.001**); the
#    war-premium proxy, and *why* inventories are overridden (lifts daily R² 0.28→0.34).
# 3. **Equities / risk (S&P)** — secondary (insignificant, p=0.40).
#    *(DXY + news together ARE the one geopolitical regime, expressed two ways. The inventory
#    surprise ranks **below all of these** — event-level, insignificant.)*
#
# **Framework (one line):** surprise (`EIA−API`) → two-stage abnormal-return event study →
# regime/amplifier overlay (backwardation, vol, **news sentiment** as the dominant offset) →
# spread routing. The honest verdict: in this geopolitics-dominated regime the EIA print is a
# **secondary driver**; news doesn't predict the print but **explains the tape and ranks among
# the top drivers (#2, just behind the dollar)** — which is the reasoning behind the NEUTRAL call.
