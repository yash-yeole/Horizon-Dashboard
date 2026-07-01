#!/usr/bin/env python
# coding: utf-8

# # Phase 1 - Data Layer
# 
# Builds a **clean daily feature panel** for the regime framework, starting with **CL (WTI)**.
# 
# What this notebook produces (cached to `cache/`):
# - Daily curve snapshot (last 1-min obs per UTC day) for `c1..cN` weighted-mid.
# - **Target structure:** `c1-c2` calendar spread.
# - **Volatility feature:** realized vol of `c1` from intraday 1-min log returns.
# - **Curve features:** slope (`c1-c2`), and PCA level/slope/curvature (PCA fit on TRAIN only -> no lookahead).
# - **Seasonal features:** month `sin/cos`, day-of-year, approx days-to-expiry of the front contract.
# - **Fundamentals (optional):** EIA / FRED / yfinance, point-in-time aligned. Skipped gracefully if keys/internet absent.
# - **Train/test split** at `2026-03-01` (test = trailing months; data ends 2026-05-22).
# 
# Design reference: regimes classified daily; 1-min data only used to compute features.

# In[1]:


import os, re, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 50)

# ---- config ----
DATA_DIR  = Path("../data")
CACHE_DIR = Path("cache"); CACHE_DIR.mkdir(exist_ok=True)
INSTRUMENT = "CL"                       # focus instrument for Phase 1
DATA_FILE  = DATA_DIR / f"{INSTRUMENT}_data.csv"
DEPTH      = 12                         # curve depth used for PCA features
TEST_START = pd.Timestamp("2026-03-01")  # everything >= this date is test
print("data file:", DATA_FILE, "exists:", DATA_FILE.exists())


# ## 1. Load the 1-min curve
# Read only `timestamp`, every `cN||weighted_mid`, and the front two contract symbols. The first line of the file is a `#meta` comment, so we skip it.

# In[2]:


def load_curve(path, depth=DEPTH):
    wm_cols   = [f"c{i}||weighted_mid" for i in range(1, depth+1)]
    con_cols  = ["c1||contract", "c2||contract"]
    keep      = set(["timestamp"] + wm_cols + con_cols)
    df = pd.read_csv(
        path, skiprows=1,                       # skip the #meta line
        usecols=lambda c: c in keep,
        parse_dates=["timestamp"],
    )
    df = df.sort_values("timestamp").set_index("timestamp")
    return df

raw = load_curve(DATA_FILE)
print("rows:", f"{len(raw):,}", "| span:", raw.index.min(), "->", raw.index.max())
raw.head(3)


# ## 2. Resample to a daily panel
# For each UTC day we take the **last** non-null observation of each column (a settle-like snapshot) and the number of 1-min obs that day. Realized vol is computed from the full intraday `c1` series.

# In[3]:


wm_cols = [f"c{i}||weighted_mid" for i in range(1, DEPTH+1)]
day = raw.index.normalize()

# last obs per day for each weighted-mid + front contract symbols
daily = raw.groupby(day).last()
daily["n_obs"] = raw.groupby(day).size()
daily.index.name = "date"

# realized vol of c1 from intraday 1-min log returns
c1 = raw["c1||weighted_mid"].astype(float)
logret = np.log(c1).diff()
rv = logret.groupby(raw.index.normalize()).std()      # daily std of 1-min log returns
daily["rv_c1"] = rv
daily["rv_c1_ann"] = daily["rv_c1"] * np.sqrt(252 * 1440)   # annualized (informational)

print("daily rows:", len(daily))
daily[["c1||weighted_mid","c2||weighted_mid","n_obs","rv_c1"]].tail(3)

daily.index = daily.index.tz_localize(None)  # UTC wall-time -> naive for clean date math


# ## 3. Structure, curve & seasonal features

# In[4]:


f = pd.DataFrame(index=daily.index)

# --- target structure: front calendar spread ---
f["c1"] = daily["c1||weighted_mid"].astype(float)
f["c2"] = daily["c2||weighted_mid"].astype(float)
f["cal_1_2"] = f["c1"] - f["c2"]            # >0 backwardation, <0 contango for WTI

# --- volatility feature ---
f["rv_c1"] = daily["rv_c1"]

# --- curve slope (also used for the curve regime axis later) ---
f["slope_1_2"] = f["cal_1_2"]
f["slope_pct"] = (f["c1"] - f["c2"]) / f["c2"]

# --- PCA level/slope/curvature on the curve (fit on TRAIN only) ---
curve = daily[wm_cols].astype(float)
curve_full = curve.dropna()                 # need full curve for clean PCA
train_mask = curve_full.index < TEST_START
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler().fit(curve_full[train_mask])
pca = PCA(n_components=3).fit(scaler.transform(curve_full[train_mask]))
comps = pca.transform(scaler.transform(curve_full))
pcdf = pd.DataFrame(comps, index=curve_full.index,
                    columns=["pc_level","pc_slope","pc_curve"])
f = f.join(pcdf)
print("PCA explained var (train):", np.round(pca.explained_variance_ratio_, 3))

# --- seasonal features ---
doy = f.index.dayofyear
f["seas_sin"] = np.sin(2*np.pi*doy/365.25)
f["seas_cos"] = np.cos(2*np.pi*doy/365.25)
f["month"] = f.index.month

# --- approx days-to-expiry of front contract ---
MONTH_CODE = dict(zip("FGHJKMNQUVXZ", range(1,13)))
def front_expiry(sym):
    if not isinstance(sym, str): return np.nan
    m = re.match(r"^[A-Z]{2}([FGHJKMNQUVXZ])(\d{1,2})$", sym)
    if not m: return np.nan
    mon = MONTH_CODE[m.group(1)]; yr = int(m.group(2))
    yr = 2000+yr if yr >= 10 else 2020+yr
    # WTI expires ~20th of the month BEFORE the delivery month (approx)
    deliv = pd.Timestamp(year=yr, month=mon, day=1)
    exp = deliv - pd.Timedelta(days=11)
    return exp
exp = daily["c1||contract"].map(front_expiry)
f["front_contract"] = daily["c1||contract"]
f["days_to_expiry"] = (exp - f.index.to_series()).dt.days

f.tail(3)


# ## 4. Fundamentals (EIA / FRED / yfinance) - point-in-time, optional
# These run only if keys are in `.env` and there is internet. Each source is wrapped so a failure just prints a notice and the panel still builds from curve features.

# In[5]:


from dotenv import load_dotenv
load_dotenv()
EIA_KEY  = os.getenv("EIA_API_KEY") or ""
FRED_KEY = os.getenv("FRED_API_KEY") or ""

fund = pd.DataFrame(index=f.index)

# ---- yfinance: non-revised market state (no key needed) ----
try:
    import yfinance as yf
    yq = yf.download(["^VIX","DX-Y.NYB","^GSPC"], start="2020-12-01",
                     progress=False)["Close"]
    yq = yq.rename(columns={"^VIX":"vix","DX-Y.NYB":"dxy","^GSPC":"spx"})
    yq.index = pd.to_datetime(yq.index).tz_localize(None)
    fund = fund.join(yq.reindex(f.index))
    print("yfinance: ok", list(yq.columns))
except Exception as e:
    print("yfinance skipped:", repr(e)[:120])

# ---- FRED: macro overlay (needs key) ----
if FRED_KEY:
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_KEY)
        series = {"dgs10":"DGS10","t10yie":"T10YIE","dtwexbgs":"DTWEXBGS"}
        for name, sid in series.items():
            s = fred.get_series(sid)
            s.index = pd.to_datetime(s.index)
            fund[name] = s.reindex(f.index).ffill()
        print("FRED: ok", list(series))
    except Exception as e:
        print("FRED skipped:", repr(e)[:120])
else:
    print("FRED skipped: no FRED_API_KEY in .env")

# ---- EIA v2: inventory core (needs key), point-in-time via release lag ----
if EIA_KEY:
    try:
        import requests
        def eia_weekly(series_id):
            url = ("https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
                   f"?api_key={EIA_KEY}&frequency=weekly&data[0]=value"
                   f"&facets[series][]={series_id}&sort[0][column]=period"
                   "&sort[0][direction]=asc&length=5000")
            rec = pd.DataFrame(requests.get(url, timeout=30).json()["response"]["data"])
            rec["period"] = pd.to_datetime(rec["period"])
            rec["value"]  = pd.to_numeric(rec["value"])
            rec["avail"]  = rec["period"] + pd.Timedelta(days=5)   # ~Wed release lag
            return rec.sort_values("avail")[["avail","value"]]
        def seas_z(col):                       # z vs same ISO-week history, expanding
            wk = f.index.isocalendar().week.values
            z = pd.Series(index=f.index, dtype=float)
            for w in np.unique(wk):
                m = wk == w; h = col[m].expanding()
                z[m] = (col[m] - h.mean()) / h.std()
            return z
        # national crude (broad regime) + Cushing (WTI delivery point -> drives front calendar)
        EIA_SERIES = {"eia_crude_stocks": "WCESTUS1",
                      "eia_cushing_stocks": "W_EPC0_SAX_YCUOK_MBBL"}
        for name, sid in EIA_SERIES.items():
            rec = eia_weekly(sid)
            merged = pd.merge_asof(
                pd.DataFrame({"date": f.index}).sort_values("date"),
                rec.rename(columns={"value": name}),
                left_on="date", right_on="avail", direction="backward")
            fund[name] = merged.set_index("date")[name]
            fund[name + "_seas_z"] = seas_z(fund[name])
        print("EIA: ok", list(EIA_SERIES))
    except Exception as e:
        print("EIA skipped:", repr(e)[:160])
else:
    print("EIA skipped: no EIA_API_KEY in .env")

panel = f.join(fund)
print("panel cols:", list(panel.columns))


# ## 5. Train/test split & cache

# In[6]:


panel = panel.sort_index()
panel["split"] = np.where(panel.index < TEST_START, "train", "test")

# drop days with too few intraday obs (illiquid / holiday stubs) using a soft floor
panel = panel.join(daily["n_obs"])
panel = panel[panel["n_obs"].fillna(0) >= 60]

out = CACHE_DIR / f"{INSTRUMENT}_daily_panel.parquet"
panel.to_parquet(out)
print("saved:", out)
print(panel["split"].value_counts())
print("train span:", panel[panel.split=='train'].index.min(), "->",
      panel[panel.split=='train'].index.max())
print("test  span:", panel[panel.split=='test'].index.min(), "->",
      panel[panel.split=='test'].index.max())
panel.tail(3)


# ## 6. Sanity checks
# No-lookahead spot checks + a look at the target series and vol.

# In[7]:


import matplotlib.pyplot as plt

assert panel.index.is_monotonic_increasing, "dates not sorted"
assert not panel.index.duplicated().any(), "duplicate dates"
print("rows:", len(panel), "| NaN in cal_1_2:", int(panel['cal_1_2'].isna().sum()))
print(panel[["c1","c2","cal_1_2","rv_c1","slope_pct","days_to_expiry"]].describe().round(3))

fig, ax = plt.subplots(3, 1, figsize=(11,8), sharex=True)
ax[0].plot(panel.index, panel["cal_1_2"]); ax[0].axhline(0, color="k", lw=.5)
ax[0].set_title("CL c1-c2 calendar spread (>0 backwardation)")
ax[1].plot(panel.index, panel["rv_c1"]); ax[1].set_title("c1 realized vol (1-min)")
ax[2].plot(panel.index, panel["cal_1_2"]/panel["c2"]); ax[2].set_title("slope %")
for a in ax: a.axvline(TEST_START, color="r", ls="--", lw=.8)
plt.tight_layout(); plt.show()

