"""PHASE A — honest walk-forward evaluation + z-compression diagnosis (read-only).

Replaces the single 21-day holdout with expanding-window walk-forward: refit the
fair-value model every STEP trading days, predict the next STEP-day block strictly
out-of-sample, accumulate residuals across the full history.  Then answer the two
questions that decide the rebuild:

  Q1  Is z compressed because the NUMERATOR is too small (fair value HUGS the
      spread) or because the DENOMINATOR (resid_std) is too big?
        - anchor_stability = std(d fair_value) / std(d spread).
            ~0  => slow stable anchor (good).   ~1 => fair value tracks the spread
            (hugging) -> deviations vanish -> z can't travel.
        - denom audit: resid_std actually used vs realized OOS residual std, and
          how much the feat_dist/DIST_D0 inflation contributes.
  Q2  Is the residual a healthy mean-reverting z-process?
        - z dispersion: std (target ~1), %|z|>1 (~30%), %|z|>2 (~5%), max tail (3-5).
        - bias mean + t-stat (systematic LONG/SHORT tilt).
        - reversion corr(resid_t, dSpread_t+1)<0 and hit-rate>0.5.
        - R^2 and skill vs random walk.

Causality: score_regimes uses EXPANDING terciles, so regime labels are already
causal; we compute them once. fit_fairvalue trains only on split=="train", which we
set to everything strictly before each OOS block -> no leakage.

Run with venv/system python that has sklearn; REGIME_MODEL_DIR auto-set.
  STEP env  : block / refit cadence in trading days (default 21 = monthly).
  MIN_TRAIN : first block starts once train has >= this many rows (default 320).
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault(
    "REGIME_MODEL_DIR",
    os.path.abspath(os.path.join(HERE, "..", "..", "..", "Regime", "model")),
)
sys.path.insert(0, os.path.join(HERE, "strategy"))
import numpy as np, pandas as pd
import fair_value as fv

COMBOS = [("CL", "cal", "WTI"), ("CL", "fly", "WTI"),
          ("CO", "cal", "Brent"), ("CO", "fly", "Brent")]
STEP = int(os.environ.get("STEP", 21))
MIN_TRAIN = int(os.environ.get("MIN_TRAIN", 320))


def _fmt(x, f="{:.3f}"):
    try:
        return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f.format(x)
    except Exception:
        return "n/a"


def assemble(product, target):
    """Build the scored daily `reg` frame ONCE (panel + causal regimes), reusing
    the exact pipeline fair_value.scored_daily uses up to score_regimes."""
    pipeline = fv._import_pipeline()
    model_inst = {"CL": "CL", "CO": "LCO"}.get(product, product)
    cwd = os.getcwd(); os.chdir(fv.MODEL_DIR)
    try:
        hist = pipeline.daily_panel(model_inst)
        db_rows = fv._db_daily_rows(product)
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
    finally:
        os.chdir(cwd)
    return pipeline, reg


def walk_forward(product, target, instrument):
    pipeline, reg = assemble(product, target)
    reg = reg.dropna(subset=[target, "c1"]).copy()
    n = len(reg)
    idx = reg.index
    starts = list(range(MIN_TRAIN, n, STEP))
    blocks = []
    cwd = os.getcwd(); os.chdir(fv.MODEL_DIR)
    try:
        for s in starts:
            e = min(s + STEP, n)
            r = reg.copy()
            split = np.where(np.arange(n) < s, "train", "test").astype(object)
            r["split"] = split
            try:
                sig = pipeline.run_structure(r, target, instrument, "c1-c2")
            except Exception:
                continue
            if sig is None:
                continue
            blk = sig.iloc[s:e]
            blocks.append(blk[[c for c in ["fair_value", "residual", "resid_std_train",
                              "z", "actual", "regime_eff", "feat_dist", target]
                              if c in blk.columns]])
    finally:
        os.chdir(cwd)
    if not blocks:
        return None
    oos = pd.concat(blocks).sort_index()
    oos = oos[~oos.index.duplicated(keep="first")]
    return oos


def diagnose(product, target, instrument):
    oos = walk_forward(product, target, instrument)
    print(f"\n=== {instrument} {target} ({product}) ===")
    if oos is None or len(oos) < 30:
        print("  insufficient OOS rows"); return None

    a = oos["actual"].astype(float) if "actual" in oos else oos[target].astype(float)
    f = oos["fair_value"].astype(float)
    resid = (a - f)
    z = oos["z"].astype(float)
    n = len(oos)

    # Q1 numerator vs denominator
    d_fair = f.diff().dropna()
    d_act = a.diff().dropna()
    anchor_stab = float(d_fair.std() / d_act.std()) if d_act.std() > 0 else float("nan")
    realized_resid_std = float(resid.std(ddof=1))
    used_std = float(oos["resid_std_train"].astype(float).mean()) if "resid_std_train" in oos else float("nan")
    denom_ratio = used_std / realized_resid_std if realized_resid_std > 0 else float("nan")

    # Q2 z-process health
    z_std = float(z.std(ddof=1))
    p_gt1 = float((z.abs() > 1).mean()); p_gt2 = float((z.abs() > 2).mean())
    z_max = float(z.abs().max())
    bias = float(resid.mean())
    bias_t = bias / (resid.std(ddof=1) / np.sqrt(n)) if resid.std(ddof=1) > 0 else float("nan")
    # reversion
    dnext = a.shift(-1) - a
    m = resid.notna() & dnext.notna()
    rev_corr = float(np.corrcoef(resid[m], dnext[m])[0, 1]) if m.sum() > 2 else float("nan")
    hit = ((resid[m] > 0) & (dnext[m] < 0)) | ((resid[m] < 0) & (dnext[m] > 0))
    rev_hit = float(hit.mean()) if m.sum() else float("nan")
    # fit quality
    ss_res = float((resid ** 2).sum()); ss_tot = float(((a - a.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    rw = a.shift(1); rwe = (a - rw).dropna()
    rmse = float(np.sqrt((resid ** 2).mean())); rmse_rw = float(np.sqrt((rwe ** 2).mean()))
    skill = 1 - rmse / rmse_rw if rmse_rw else float("nan")

    print(f"  OOS n={n}  blocks step={STEP}")
    print(f"  [Q1 numerator] anchor_stability std(dFair)/std(dSpread)={_fmt(anchor_stab)} "
          f"(0=stable anchor, 1=hugging)")
    print(f"  [Q1 denom]     resid_std_used={_fmt(used_std)}  realized_resid_std={_fmt(realized_resid_std)}  "
          f"used/realized={_fmt(denom_ratio)} (>1 => denom too big)")
    print(f"  [Q2 z-shape]   z_std={_fmt(z_std)} (~1 good)  %|z|>1={_fmt(p_gt1,'{:.0%}')} (~30%)  "
          f"%|z|>2={_fmt(p_gt2,'{:.0%}')} (~5%)  max|z|={_fmt(z_max,'{:.1f}')}")
    print(f"  [Q2 bias]      mean_resid={_fmt(bias,'{:+.3f}')} (t={_fmt(bias_t,'{:+.1f}')})")
    print(f"  [Q2 reversion] corr={_fmt(rev_corr,'{:+.3f}')}  hit={_fmt(rev_hit,'{:.0%}')} (>50% good)")
    print(f"  [Q2 fit]       R2={_fmt(r2)}  RMSE={_fmt(rmse)}  skill_vs_RW={_fmt(skill,'{:+.3f}')}")

    return dict(inst=instrument, tgt=target, n=n, anchor=anchor_stab,
                denom=denom_ratio, z_std=z_std, p1=p_gt1, p2=p_gt2,
                bias=bias, bias_t=bias_t, rev=rev_corr, hit=rev_hit, r2=r2, skill=skill)


def main():
    rows = [r for c in COMBOS if (r := diagnose(*c))]
    if not rows:
        return
    df = pd.DataFrame(rows)
    print("\n================ WALK-FORWARD SUMMARY ================")
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(df.to_string(index=False, float_format=lambda v: _fmt(v)))
    print("\nDIAGNOSIS KEY:")
    print("  anchor ~1  => fair value hugs spread (NUMERATOR problem) -> rebuild anchor slower")
    print("  denom  >1  => resid_std too big (DENOMINATOR problem)     -> recalibrate z denom")
    print("  z_std <<1 + low %|z|>1 => compressed z (the no-trade symptom)")
    print("  |bias_t|>2 => systematic long/short tilt -> de-bias")
    print("  rev<0 & hit>50% => fair value is a real attractor (edge exists)")


if __name__ == "__main__":
    main()
