"""
fair_value.py — bridge the trained Phase 1-6 model to the intraday DB bars.

Goal: for every trading day covered by the strategy DB files, attach
    * the daily regime label (3-axis, effective)
    * the daily fair value of the c1-c2 spread (from the trained model)
    * resid_std_train[regime]  (the z denominator)
without re-fitting anything new: the model trains on split=="train"
(pre-2026-03-01) and scores the DB days forward.

Then, intraday, fair value + regime are held constant within a day and the
live 15-min spread is compared against them:
    z(t) = (spread_live(t) - fair_value_day) / resid_std_train[regime_day]

This respects the locked framework (regime classified daily, never per-bar)
while giving a 15-min decision cadence.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import pandas as pd

# make model/pipeline.py importable and run with CWD=model so its relative
# paths (../data, cache/) resolve exactly as in the notebooks.
HERE = os.path.dirname(os.path.abspath(__file__))
# Default to the sibling ../model dir; override via REGIME_MODEL_DIR when the
# strategy engine is vendored elsewhere (e.g. copied into the dashboard backend,
# while the trained model stays in its original Regime/model location).
MODEL_DIR = os.environ.get(
    "REGIME_MODEL_DIR",
    os.path.abspath(os.path.join(HERE, "..", "model")),
)
if MODEL_DIR not in sys.path:
    sys.path.insert(0, MODEL_DIR)

import data_feed as feed  # noqa: E402


def _import_pipeline():
    """Import pipeline with CWD switched to model/ so ../data + cache resolve."""
    cwd = os.getcwd()
    os.chdir(MODEL_DIR)
    try:
        import pipeline  # noqa: WPS433
        import importlib
        importlib.reload(pipeline)
    finally:
        os.chdir(cwd)
    return pipeline


# ------------------------------------------------- daily rows from the DB bars
def _db_daily_rows(product: str = "CL", depth: int = 12) -> pd.DataFrame:
    """Build daily-panel-shaped rows from the 15-min DB bars (one row per day).

    Columns mirror pipeline.daily_panel: c1,c2,c3,cal,fly,rv,slope_pct,level,
    seas_sin,seas_cos,days_to_expiry,split.
    Uses a SINGLE connection per DB file to avoid repeated connection overhead.
    """
    pipeline = _import_pipeline()
    rows = []
    for db in feed.list_db_files():
        as_of = feed._date_from_path(db)
        # one connection for the whole file
        conn = feed._connect(db)
        all_tabs = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        prod_tabs = [t for t in all_tabs if t.startswith(product + "_")]
        tenors_all = [t.split("_", 1)[1] for t in prod_tabs]
        rows_exp = [(t, feed._expiry(t)) for t in tenors_all if pd.notna(feed._expiry(t))]
        if as_of and pd.notna(as_of):
            rows_exp = [(t, e) for t, e in rows_exp
                        if e >= as_of.normalize().replace(day=1)]
        rows_exp.sort(key=lambda x: x[1])
        tenors = [t for t, _ in rows_exp[:depth]]
        if len(tenors) < 3:
            conn.close(); continue
        # read all needed tables in one connection pass
        closes = {}
        for t in tenors:
            try:
                df = pd.read_sql(f'SELECT timestamp, close FROM "{product}_{t}" '
                                 f'ORDER BY timestamp', conn,
                                 parse_dates=["timestamp"]).set_index("timestamp")
                closes[t] = df["close"]
            except Exception:  # noqa: BLE001
                pass
        conn.close()
        cur = pd.DataFrame(closes)
        cur["day"] = cur.index.normalize()
        for day, g in cur.groupby("day"):
            last = g.drop(columns="day").ffill().iloc[-1]
            c1 = last.get(tenors[0]); c2 = last.get(tenors[1]); c3 = last.get(tenors[2])
            if pd.isna(c1) or pd.isna(c2) or pd.isna(c3):
                continue
            # realized vol from intraday log-returns of the front contract
            fc = g[tenors[0]].dropna()
            rv = float(np.log(fc).diff().std()) if len(fc) > 3 else np.nan
            level = float(g.drop(columns="day").iloc[-1].mean(skipna=True))
            doy = pd.Timestamp(day).dayofyear
            exp = feed._expiry(tenors[0])  # month-start placeholder ~ expiry-11d
            dte = (exp - pd.Timedelta(days=11) - pd.Timestamp(day)).days if pd.notna(exp) else np.nan
            rows.append({
                "date": pd.Timestamp(day), "c1": c1, "c2": c2, "c3": c3,
                "cal": c1 - c2, "fly": c1 - 2 * c2 + c3, "def23": c2 - c3, "rv": rv,
                "slope_pct": (c1 - c2) / c2, "level": level,
                "seas_sin": np.sin(2 * np.pi * doy / 365.25),
                "seas_cos": np.cos(2 * np.pi * doy / 365.25),
                "days_to_expiry": dte, "split": "test",
            })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("date").sort_index()


# ------------------------------------------------- scored daily panel (model)
def scored_daily(product: str = "CL", target: str = "cal",
                 instrument: str = "WTI", structure: str = "c1-c2") -> pd.DataFrame:
    """Full daily panel (history + DB days) scored with the trained model.

    Returns the pipeline.make_signals frame: includes regime_eff, fair_value,
    residual, resid_std_train, z, state, ood, confidence, near_boundary, split.
    The DB days appear at the tail with split=="test".
    """
    pipeline = _import_pipeline()
    model_inst = {"CL": "CL", "CO": "LCO"}.get(product, product)  # Brent curve csv = LCO

    cwd = os.getcwd()
    os.chdir(MODEL_DIR)
    try:
        hist = pipeline.daily_panel(model_inst)              # csv history -> daily features
        db_rows = _db_daily_rows(product)                    # DB days -> same shape
        if not db_rows.empty:
            db_rows = db_rows[~db_rows.index.isin(hist.index)]
            cols = [c for c in hist.columns if c in db_rows.columns]
            panel = pd.concat([hist, db_rows[cols].reindex(columns=hist.columns)])
        else:
            panel = hist
        panel = panel[~panel.index.duplicated(keep="last")].sort_index()
        fund = pipeline.fetch_fundamentals(panel.index)
        panel = panel.join(fund)
        reg = pipeline.score_regimes(panel)
        sig = pipeline.run_structure(reg, target, instrument, structure)
    finally:
        os.chdir(cwd)
    return sig


# ------------------------------------------------- per-day fair-value map
_CACHE_DIR = os.path.join(HERE, "cache")


def _latest_bar_ts(product: str) -> pd.Timestamp | None:
    """Timestamp of the newest bar row across all DB files for this product."""
    latest = None
    for db in feed.list_db_files():
        try:
            conn = feed._connect(db)
            tabs = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                    if r[0].startswith(product + "_")]
            for t in tabs[:1]:  # one table is enough to get the latest ts
                mx = conn.execute(
                    f'SELECT MAX(timestamp) FROM "{t}"').fetchone()[0]
                if mx:
                    ts = pd.Timestamp(mx)
                    if latest is None or ts > latest:
                        latest = ts
            conn.close()
        except Exception:  # noqa: BLE001
            pass
    return latest


def daily_fairvalue_map(product: str = "CL", target: str = "cal",
                        force_recompute: bool = False) -> pd.DataFrame:
    """One row per DB trading day: regime, fair_value, resid_std, confidence, etc.

    Cached to parquet so repeat calls are instant.  Cache is invalidated whenever
    the newest bar timestamp in the DB advances (i.e. new data has arrived).
    Pass force_recompute=True to rebuild unconditionally.
    """
    os.makedirs(_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(_CACHE_DIR, f"fv_{product}_{target}.parquet")
    meta_path  = cache_path + ".meta"

    # check if cache is still fresh
    if not force_recompute and os.path.exists(cache_path):
        latest_ts = _latest_bar_ts(product)
        cached_ts = open(meta_path).read().strip() if os.path.exists(meta_path) else ""
        if latest_ts is not None and str(latest_ts) == cached_ts:
            return pd.read_parquet(cache_path)

    # (re)compute
    print(f"fair_value: computing daily fair-value map for {product}/{target} "
          f"(first run or new DB data) …")
    sig = scored_daily(product, target)
    db_rows = _db_daily_rows(product)
    db_days = db_rows.index.normalize() if not db_rows.empty else pd.DatetimeIndex([])
    keep = sig[sig.index.normalize().isin(db_days)]
    cols = ["regime_eff", "inv", "vol", "curve", "fair_value", "fv_drift", "residual",
            "resid_std_train", "z", "state", "ood", "confidence",
            "near_boundary", "regime_n", "actual"]
    cols = [c for c in cols if c in keep.columns]
    result = keep[cols].copy()

    # save cache + metadata (latest bar ts as sentinel)
    result.to_parquet(cache_path)
    latest_ts = _latest_bar_ts(product)
    with open(meta_path, "w") as f:
        f.write(str(latest_ts) if latest_ts else "")
    print(f"fair_value: cached to {cache_path}")
    return result


if __name__ == "__main__":
    fvm = daily_fairvalue_map("CL")
    print("DB days scored:", len(fvm))
    show = ["regime_eff", "fair_value", "resid_std_train", "actual", "z",
            "ood", "confidence"]
    print(fvm[[c for c in show if c in fvm.columns]].to_string())
