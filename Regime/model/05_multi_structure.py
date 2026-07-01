#!/usr/bin/env python
# coding: utf-8

# # Phase 5 - All Structures
# 
# Runs the full pipeline (regimes -> fair value -> signals) for every structure using `pipeline.py`:
# - **Calendar (c1-c2)** and **Butterfly (c1-2c2+c3)** for CL, HO, LCO, LGO, and the WTI-Brent spread curve.
# - **Cracks:** heating (HO*42 - CL) on the CL regime; gasoil (LGO/7.45 - LCO) on the Brent regime.
# 
# Regimes are computed **once per instrument** (national inventory + that instrument's vol & curve) and shared by its structures. Output: one combined signal book `cache/all_signals.parquet`.

# In[1]:


import importlib, pipeline as P
importlib.reload(P)
import pandas as pd, numpy as np
from pathlib import Path
CACHE=Path("cache")
INSTRUMENTS=["CL","HO","LCO","LGO","wtcl_lco_outrights"]
LABEL={"CL":"WTI","HO":"HeatingOil","LCO":"Brent","LGO":"Gasoil","wtcl_lco_outrights":"WTI-Brent"}

panels={}; regs={}
for inst in INSTRUMENTS:
    f=P.daily_panel(inst)
    panel=f.join(P.fetch_fundamentals(f.index))
    regs[inst]=P.score_regimes(panel); panels[inst]=f
    print(f"{inst:20s} rows={len(regs[inst]):4d} regimes={regs[inst]['regime_eff'].nunique()}")


# ## Calendar + Butterfly for every instrument

# In[2]:


books=[]
for inst in INSTRUMENTS:
    for struct,target in [("c1-c2","cal"),("butterfly","fly")]:
        sig=P.run_structure(regs[inst].copy(), target, LABEL[inst], struct)
        if sig is not None:
            books.append(sig);
            te=sig[sig.split=='test']
            print(f"{LABEL[inst]:10s} {struct:9s} model={sig['_chosen'].iloc[0]:5s} "
                  f"test_OOD={int(te.ood.sum()):2d}/{len(te)} "
                  f"active_eps={sig['episode'].nunique()}")


# ## Cracks (cross-instrument, on the crude regime)

# In[3]:


def add_crack(crude, prod, name, conv):
    r=regs[crude].copy()
    p1=panels[prod]["c1"].reindex(r.index)
    r[name]=p1*conv - r["c1"]
    return P.run_structure(r, name, LABEL[crude]+"-"+LABEL[prod], name)

heat=add_crack("CL","HO","crack_heating",42.0)       # $/gal -> $/bbl
gas =add_crack("LCO","LGO","crack_gasoil",1/7.45)    # $/tonne -> $/bbl
for sig,nm in [(heat,"heating crack"),(gas,"gasoil crack")]:
    if sig is not None:
        books.append(sig); te=sig[sig.split=='test']
        print(f"{nm:14s} model={sig['_chosen'].iloc[0]:5s} test_OOD={int(te.ood.sum())}/{len(te)}")


# ## Combine & save the signal book

# In[4]:


cols=["instrument","structure","actual","fair_value","residual","z","direction",
      "state","ood","episode","confidence","regime_eff","regime_level","near_boundary",
      "regime_n","resid_std_train","split"]
allsig=pd.concat([b.assign(date=b.index)[["date"]+cols] for b in books], ignore_index=True)
allsig=allsig.set_index("date").sort_index()
allsig.to_parquet(CACHE/"all_signals.parquet")
print("saved all_signals.parquet | rows:", len(allsig),
      "| structures:", allsig.groupby(['instrument','structure']).ngroups)
allsig.groupby(["instrument","structure"]).size().rename("rows")


# ## Sanity: latest cross-sectional opportunity board

# In[5]:


latest=allsig.index.max()
cur=allsig.loc[[latest]] if latest in allsig.index else allsig.tail(20)
board=cur[cur.state.isin(["ENTRY","HOLD"])].assign(absz=lambda d:d.z.abs())
print("as of", latest.date())
board.sort_values("absz",ascending=False)[["instrument","structure","regime_eff",
    "actual","fair_value","z","direction","confidence"]].round(2)

