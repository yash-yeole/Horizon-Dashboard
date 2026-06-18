"""
Reusable regime -> fair-value -> signal pipeline.
Ports the proven logic from notebooks 01-04 into functions so it can run for any
instrument / structure. Imported by 05_multi_structure.ipynb and 06_dashboard.ipynb.
"""
import os, re
import numpy as np, pandas as pd
from pathlib import Path
from sklearn.linear_model import LinearRegression, Ridge, ElasticNet, RidgeCV, ElasticNetCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

DATA = Path("../data"); CACHE = Path("cache"); CACHE.mkdir(exist_ok=True)
TEST_START = pd.Timestamp("2026-03-01")

# regime / model / signal constants (identical to phases 2-4)
SMOOTH, HYST, WARMUP, MIN_N = 5, 0.15, 252, 60
K_POOL, MARGIN, N_SPLITS = 100, 0.02, 5
ENTRY, EXIT, STOP, Z_EXTREME = 2.0, 0.5, 3.0, 4.0
MONTH_CODE = dict(zip("FGHJKMNQUVXZ", range(1, 13)))

FEATURES = ["eia_crude_stocks_seas_z", "eia_cushing_stocks_seas_z", "rv", "vix",
            "dxy", "dgs10", "t10yie", "dtwexbgs", "seas_sin", "seas_cos",
            "days_to_expiry", "level"]

# ----------------------------------------------------------------------------- load
def _resolve_file(instrument):
    for cand in (f"{instrument}_data.csv", f"{instrument}_1min.csv"):
        if (DATA / cand).exists(): return DATA / cand
    raise FileNotFoundError(instrument)

def load_curve(instrument, depth=12):
    path = _resolve_file(instrument)
    wm = [f"c{i}||weighted_mid" for i in range(1, depth+1)]
    keep = set(["timestamp", "c1||contract"] + wm)
    df = pd.read_csv(path, skiprows=1, usecols=lambda c: c in keep,
                     parse_dates=["timestamp"]).sort_values("timestamp").set_index("timestamp")
    return df

def daily_panel(instrument, depth=12):
    raw = load_curve(instrument, depth)
    wm = [c for c in raw.columns if c.endswith("||weighted_mid")]
    day = raw.index.normalize()
    daily = raw.groupby(day).last()
    daily["n_obs"] = raw.groupby(day).size()
    c1 = raw["c1||weighted_mid"].astype(float)
    rv = np.log(c1).diff().groupby(raw.index.normalize()).std()
    daily["rv"] = rv
    daily.index = daily.index.tz_localize(None); daily.index.name = "date"
    daily = daily[daily["n_obs"].fillna(0) >= 60]

    f = pd.DataFrame(index=daily.index)
    f["c1"] = daily["c1||weighted_mid"].astype(float)
    f["c2"] = daily["c2||weighted_mid"].astype(float)
    f["c3"] = daily["c3||weighted_mid"].astype(float)
    f["cal"] = f["c1"] - f["c2"]                       # calendar spread
    f["fly"] = f["c1"] - 2*f["c2"] + f["c3"]           # butterfly
    f["rv"] = daily["rv"]
    f["slope_pct"] = (f["c1"] - f["c2"]) / f["c2"]
    f["level"] = daily[wm].astype(float).mean(axis=1)  # curve level proxy
    doy = f.index.dayofyear
    f["seas_sin"] = np.sin(2*np.pi*doy/365.25); f["seas_cos"] = np.cos(2*np.pi*doy/365.25)
    f["days_to_expiry"] = _days_to_expiry(daily["c1||contract"], f.index)
    f["split"] = np.where(f.index < TEST_START, "train", "test")
    return f

def _days_to_expiry(sym_series, idx):
    def exp(sym):
        if not isinstance(sym, str): return np.nan
        m = re.match(r"^[A-Z]{2,4}([FGHJKMNQUVXZ])(\d{1,2})$", sym)
        if not m: return np.nan
        mon = MONTH_CODE[m.group(1)]; yr = int(m.group(2))
        yr = 2000+yr if yr >= 10 else 2020+yr
        return pd.Timestamp(year=yr, month=mon, day=1) - pd.Timedelta(days=11)
    e = pd.to_datetime(sym_series.map(exp))
    e.index = idx
    return (e - idx.to_series()).dt.days

# --------------------------------------------------------------------- fundamentals
_FUND_CACHE = {}
def fetch_fundamentals(index):
    """Fetch EIA/FRED/yfinance once; reindex to a given daily index."""
    key = (index.min(), index.max())
    if "frame" not in _FUND_CACHE:
        from dotenv import dotenv_values
        env = dotenv_values(".env")
        full = pd.date_range("2021-01-01", index.max(), freq="D")
        fund = pd.DataFrame(index=full)
        # yfinance
        try:
            import yfinance as yf
            yq = yf.download(["^VIX","DX-Y.NYB","^GSPC"], start="2020-12-01",
                             progress=False)["Close"].rename(
                             columns={"^VIX":"vix","DX-Y.NYB":"dxy","^GSPC":"spx"})
            yq.index = pd.to_datetime(yq.index).tz_localize(None)
            for c in yq.columns: fund[c] = yq[c].reindex(full).ffill()
        except Exception as e: print("yfinance skipped:", repr(e)[:80])
        # FRED
        try:
            from fredapi import Fred
            fred = Fred(api_key=env.get("FRED_API_KEY"))
            for name, sid in {"dgs10":"DGS10","t10yie":"T10YIE","dtwexbgs":"DTWEXBGS"}.items():
                ss = fred.get_series(sid); ss.index = pd.to_datetime(ss.index)
                fund[name] = ss.reindex(full).ffill()
        except Exception as e: print("FRED skipped:", repr(e)[:80])
        # EIA national + Cushing, point-in-time + seasonal z
        try:
            import requests
            k = env.get("EIA_API_KEY")
            def eia_weekly(sid):
                url=("https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
                     f"?api_key={k}&frequency=weekly&data[0]=value&facets[series][]={sid}"
                     "&sort[0][column]=period&sort[0][direction]=asc&length=5000")
                r=pd.DataFrame(requests.get(url,timeout=30).json()["response"]["data"])
                r["period"]=pd.to_datetime(r["period"]); r["value"]=pd.to_numeric(r["value"])
                r["avail"]=r["period"]+pd.Timedelta(days=5)
                return r.sort_values("avail")[["avail","value"]]
            def seas_z(col):
                wk=col.index.isocalendar().week.values
                z=pd.Series(index=col.index,dtype=float)
                for w in np.unique(wk):
                    m=wk==w; h=col[m].expanding(); z[m]=(col[m]-h.mean())/h.std()
                return z
            for name,sid in {"eia_crude_stocks":"WCESTUS1",
                             "eia_cushing_stocks":"W_EPC0_SAX_YCUOK_MBBL"}.items():
                rec=eia_weekly(sid)
                mg=pd.merge_asof(pd.DataFrame({"date":full}).sort_values("date"),
                    rec.rename(columns={"value":name}),left_on="date",right_on="avail",
                    direction="backward").set_index("date")
                fund[name]=mg[name]; fund[name+"_seas_z"]=seas_z(fund[name])
        except Exception as e: print("EIA skipped:", repr(e)[:120])
        _FUND_CACHE["frame"]=fund
    return _FUND_CACHE["frame"].reindex(index)

# -------------------------------------------------------------------- regime engine
def _expanding_terciles(s):
    return (s.expanding(min_periods=WARMUP).quantile(1/3),
            s.expanding(min_periods=WARMUP).quantile(2/3))

def _hyst_tercile(s, q1, q2, frac=HYST):
    buf=(q2-q1)*frac; out=[]; prev=None
    for v,a,b,bf in zip(s.values,q1.values,q2.values,buf.values):
        if np.isnan(a) or np.isnan(v): out.append(np.nan); continue
        if prev is None: cur="L" if v<=a else ("M" if v<=b else "H")
        elif prev=="L": cur="L" if not v>a+bf else ("M" if v<=b else "H")
        elif prev=="M": cur=("L" if v<a-bf else ("H" if v>b+bf else "M"))
        else: cur="H" if not v<b-bf else ("L" if v<a-bf else "M")
        out.append(cur); prev=cur
    return pd.Series(out,index=s.index)

def score_regimes(panel):
    inv_raw = panel["eia_crude_stocks_seas_z"].fillna(panel["eia_crude_stocks"].rank(pct=True)
              if "eia_crude_stocks" in panel else panel["eia_crude_stocks_seas_z"])
    inv_s = inv_raw.rolling(SMOOTH,min_periods=1).mean()
    vol_s = panel["rv"].rolling(SMOOTH,min_periods=1).mean()
    slope_s = panel["slope_pct"].rolling(SMOOTH,min_periods=1).mean()
    absslope = slope_s.abs()
    iq1,iq2=_expanding_terciles(inv_s); vq1,vq2=_expanding_terciles(vol_s)
    inv_lab=_hyst_tercile(inv_s,iq1,iq2); vol_lab=_hyst_tercile(vol_s,vq1,vq2)
    band=absslope.expanding(min_periods=WARMUP).quantile(1/3)
    curve_lab=[]; prev=None
    for v,a,bd in zip(slope_s.values,absslope.values,band.values):
        if np.isnan(bd) or np.isnan(v): curve_lab.append(np.nan); continue
        if prev=="Flat": cur="Flat" if a<=bd*(1+HYST) else ("Back" if v>0 else "Contango")
        else: cur="Flat" if a<=bd*(1-HYST) else ("Back" if v>0 else "Contango")
        curve_lab.append(cur); prev=cur
    curve_lab=pd.Series(curve_lab,index=panel.index)
    axes=pd.DataFrame({"inv":inv_lab,"vol":vol_lab,"curve":curve_lab}).dropna()
    axes=axes.astype(str)  # force plain str (avoid pyarrow large_string concat errors)

    tr = (panel["split"]=="train").reindex(axes.index, fill_value=False)
    l0=axes["inv"]+"|"+axes["vol"]+"|"+axes["curve"]
    l1=axes["inv"]+"|*|"+axes["curve"]; l2=axes["inv"]+"|*|*"
    c0,c1,c2=l0[tr].value_counts(),l1[tr].value_counts(),l2[tr].value_counts()
    def eff(i):
        if c0.get(l0[i],0)>=MIN_N: return l0[i],0
        if c1.get(l1[i],0)>=MIN_N: return l1[i],1
        if c2.get(l2[i],0)>=MIN_N: return l2[i],2
        return "ALL",3
    reff=[eff(i) for i in axes.index]
    out=panel.join(pd.DataFrame({"inv":axes["inv"],"vol":axes["vol"],"curve":axes["curve"],
        "regime_eff":[e[0] for e in reff],"regime_level":[e[1] for e in reff]}),how="inner")
    # boundary distance + flag
    def adist(val,q1,q2):
        d=pd.concat([(val-q1).abs(),(val-q2).abs()],axis=1).min(axis=1)
        return d/val.expanding(min_periods=WARMUP).std()
    bd=pd.concat([adist(inv_s,iq1,iq2),adist(vol_s,vq1,vq2),
                  (absslope-band).abs()/absslope.expanding(min_periods=WARMUP).std()],
                 axis=1).min(axis=1).reindex(out.index)
    thr=bd.expanding(min_periods=WARMUP).quantile(0.20)
    out["boundary_dist"]=bd; out["near_boundary"]=bd<thr
    return out

# --------------------------------------------------------------------- fair value
def fit_fairvalue(reg, target, features=FEATURES):
    reg=reg.dropna(subset=[target]).copy()
    feats=[f for f in features if f in reg.columns]
    trm=(reg["split"]=="train").values
    if trm.sum()<WARMUP: return None
    imp=SimpleImputer(strategy="median").fit(reg.loc[trm,feats])
    scl=StandardScaler().fit(imp.transform(reg.loc[trm,feats]))
    X=scl.transform(imp.transform(reg[feats])); y=reg[target].values
    regime=reg["regime_eff"].values; inv=reg["inv"].values; vol=reg["vol"].values; curve=reg["curve"].values
    trp=np.where(trm)[0]; tep=np.where(~trm)[0]
    ra=RidgeCV(alphas=np.logspace(-3,3,25)).fit(X[trp],y[trp]).alpha_
    en=ElasticNetCV(l1_ratio=[.2,.5,.7,.9],alphas=np.logspace(-3,1,25),cv=5,max_iter=10000).fit(X[trp],y[trp])
    ea,el=en.alpha_,en.l1_ratio_
    def make(fam): return (LinearRegression() if fam=="ols" else
        Ridge(alpha=ra) if fam=="ridge" else ElasticNet(alpha=ea,l1_ratio=el,max_iter=10000))
    def pmask(key):
        a=key.split("|"); m=np.ones(len(reg),bool)
        if a[0]!="*": m&=inv==a[0]
        if a[1]!="*": m&=vol==a[1]
        if a[2]!="*": m&=curve==a[2]
        return m
    def pooled(trpos,prpos,fam,K=K_POOL):
        gm=make(fam).fit(X[trpos],y[trpos])
        out=pd.Series(gm.predict(X[prpos]),index=prpos)
        if K==0: return out
        for key in np.unique(regime[prpos]):
            rtr=trpos[pmask(key)[trpos]]
            if len(rtr)<20: continue
            rm=make(fam).fit(X[rtr],y[rtr]); w=len(rtr)/(len(rtr)+K)
            coef=w*rm.coef_+(1-w)*gm.coef_; ic=w*rm.intercept_+(1-w)*gm.intercept_
            pp=prpos[regime[prpos]==key]; out.loc[pp]=X[pp]@coef+ic
        return out
    # walk-forward CV
    tscv=TimeSeriesSplit(n_splits=N_SPLITS)
    oos={f:pd.Series(index=trp,dtype=float) for f in ["base","ridge","enet"]}
    for ti,vi in tscv.split(trp):
        tr,va=trp[ti],trp[vi]
        oos["base"].loc[va]=pooled(tr,va,"ols",0).values
        oos["ridge"].loc[va]=pooled(tr,va,"ridge").values
        oos["enet"].loc[va]=pooled(tr,va,"enet").values
    oos=pd.DataFrame(oos).dropna(); ya=pd.Series(y,index=range(len(y))).loc[oos.index]
    rmse=lambda a,b:np.sqrt(mean_squared_error(a,b))
    chosen="ridge" if rmse(ya,oos["ridge"])<=rmse(ya,oos["enet"]) else "enet"
    rkey=pd.Series(regime,index=range(len(regime))).loc[oos.index]
    keep={}
    for key,idx in oos.groupby(rkey).groups.items():
        keep[key]=rmse(ya.loc[idx],oos[chosen].loc[idx])<rmse(ya.loc[idx],oos["base"].loc[idx])*(1-MARGIN)
    fv_p=pooled(trp,np.arange(len(reg)),chosen); fv_b=pooled(trp,np.arange(len(reg)),"ols",0)
    fair=fv_b.copy()
    for key,kept in keep.items():
        if kept:
            mm=np.where(regime==key)[0]; fair.loc[mm]=fv_p.loc[mm]
    reg=reg.assign(fair_value=fair.sort_index().values, residual=y-fair.sort_index().values)
    rstd=reg[reg.split=="train"].groupby("regime_eff")["residual"].std().rename("resid_std_train")
    reg=reg.join(rstd,on="regime_eff")
    reg["_chosen"]=chosen; reg["_target"]=target
    return reg

# ------------------------------------------------------------------------- signals
def make_signals(reg, target, instrument, structure):
    s=reg.copy()
    std=s["resid_std_train"].replace(0,np.nan)
    s["z"]=s["residual"]/std; s["direction"]=np.where(s["z"]>0,"SHORT","LONG")
    tr=s[s.split=="train"][target]; lo,hi=tr.min(),tr.max()
    s["ood"]=(s[target]<lo)|(s[target]>hi)|(s["z"].abs()>=Z_EXTREME)
    state=[]; pos=0; pd_=0
    for zz,ood in zip(s["z"].values,s["ood"].values):
        a=abs(zz); d=1 if zz>0 else -1
        if pos==0:
            if a>=ENTRY and not ood: pos=1; pd_=d; st="ENTRY"
            elif a>=ENTRY and ood: st="DISLOCATION"
            else: st="flat"
        else:
            if d!=pd_ or a<=EXIT: pos=0; st="EXIT"
            elif a>=STOP: pos=0; st="STOP"
            else: st="HOLD"
        state.append(st)
    s["state"]=state
    active=s["state"].isin(["ENTRY","HOLD","DISLOCATION"])
    s["episode"]=(active&~active.shift(1,fill_value=False)).cumsum().where(active)
    sup=s[s.split=="train"].groupby("regime_eff").size().rename("regime_n")
    s=s.join(sup,on="regime_eff")
    def tier(r):
        if r["ood"]: return "LOW"
        if r["near_boundary"] or (r.get("regime_n",0) or 0)<60: return "MEDIUM"
        return "HIGH"
    s["confidence"]=s.apply(tier,axis=1)
    s["instrument"]=instrument; s["structure"]=structure; s["actual"]=s[target]
    return s

def run_structure(reg, target, instrument, structure):
    fitted=fit_fairvalue(reg, target)
    if fitted is None: return None
    return make_signals(fitted, target, instrument, structure)
