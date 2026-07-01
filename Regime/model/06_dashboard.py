#!/usr/bin/env python
# coding: utf-8

# # Phase 6 - Dashboard Export
# 
# Builds the four dashboard views from the cached signal book and exports a single
# `cache/dashboard.json` (+ parquet) the external dashboard can consume.
# 
# 1. **Current regime** - latest regime per instrument + confidence.
# 2. **Key drivers** - per-regime model coefficients (what sets fair value).
# 3. **Regression outputs** - fair value vs actual, residual, fit quality.
# 4. **Ranked opportunities** - active, non-dislocation signals by |z|.

# In[1]:


import importlib, pipeline as P; importlib.reload(P)
import pandas as pd, numpy as np, json
from pathlib import Path
CACHE=Path("cache")
allsig=pd.read_parquet(CACHE/"all_signals.parquet").sort_index()
latest=allsig.index.max()
print("latest date:", latest.date(), "| structures:",
      allsig.groupby(['instrument','structure']).ngroups)


# ### View 1 - Current regime (per instrument)

# In[2]:


cur=allsig.loc[[latest]]
v1=(cur.groupby("instrument").agg(regime=("regime_eff","first"),
      level=("regime_level","first"), near_boundary=("near_boundary","first"))
    .reset_index())
v1


# ### View 2 - Key drivers (latest per structure: state, z, direction, confidence)

# In[3]:


v2=cur[["instrument","structure","regime_eff","z","direction","state","confidence","ood"]]      .sort_values("z",key=lambda s:s.abs(),ascending=False).round(2)
v2


# ### View 3 - Regression outputs (fit quality per structure, test window)

# In[4]:


from sklearn.metrics import r2_score, mean_squared_error
rows=[]
for (inst,st),g in allsig.groupby(["instrument","structure"]):
    tr=g[g.split=="train"]; te=g[g.split=="test"]
    def r2(d):
        return round(r2_score(d.actual,d.fair_value),3) if len(d)>5 else np.nan
    rows.append((inst,st,len(tr),len(te),
                 round(np.sqrt(mean_squared_error(tr.actual,tr.fair_value)),3),
                 r2(tr), r2(te), int(te.ood.sum())))
v3=pd.DataFrame(rows,columns=["instrument","structure","n_train","n_test",
    "train_rmse","train_r2","test_r2","test_OOD_days"])
v3


# ### View 4 - Ranked opportunities (active, non-dislocation, by |z|)

# In[5]:


book=allsig.loc[[latest]]
book=book[book.state.isin(["ENTRY","HOLD"])].assign(abs_z=lambda d:d.z.abs())
v4=book.sort_values("abs_z",ascending=False)[["instrument","structure","regime_eff",
    "actual","fair_value","z","direction","state","confidence"]].round(2).reset_index(drop=True)
# also surface dislocation watch separately
watch=allsig.loc[[latest]]
watch=watch[watch.state=="DISLOCATION"][["instrument","structure","regime_eff","actual",
    "fair_value","z","direction"]].round(2).reset_index(drop=True)
print("TRADABLE:"); display(v4)
print("DISLOCATION WATCH:"); display(watch)


# ### Export consolidated dashboard payload

# In[6]:


payload={
  "as_of": str(latest.date()),
  "current_regime": v1.to_dict(orient="records"),
  "drivers": v2.reset_index(drop=True).to_dict(orient="records"),
  "regression_outputs": v3.to_dict(orient="records"),
  "ranked_opportunities": v4.to_dict(orient="records"),
  "dislocation_watch": watch.to_dict(orient="records"),
}
(CACHE/"dashboard.json").write_text(json.dumps(payload,indent=2,default=str))
allsig.to_parquet(CACHE/"dashboard_signals.parquet")
print("exported cache/dashboard.json and cache/dashboard_signals.parquet")
print(json.dumps(payload["ranked_opportunities"][:5],indent=2,default=str))

