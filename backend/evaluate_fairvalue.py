"""Fair-value (regime) MODEL evaluation — predictive accuracy, not just z-calibration.

For each structure, on the OUT-OF-SAMPLE (split=="test") rows we measure:
  1. Fit quality   : R^2 of fair_value vs realized spread, RMSE.
  2. Skill vs naive : RMSE(model) vs RMSE(random-walk = yesterday's spread).
                      skill = 1 - RMSE_model/RMSE_naive  ( >0 means model beats RW ).
  3. Residual bias  : mean residual (actual-fair). + => spread sits ABOVE fair
                      (rich) on avg; - => sits BELOW (cheap, LONG-biased).
  4. Mean-reversion : does a + residual today predict the spread FALLING next day
                      (and vice-versa)?  corr(residual_t, dSpread_{t+1}) should be
                      NEGATIVE if the fair value is a real attractor. Plus hit-rate
                      of "reversion happened next day".
  5. Regime use     : # distinct regimes hit OOS, resid_std spread across regimes.

Run with venv/system python that has sklearn; REGIME_MODEL_DIR auto-set.
"""
import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault(
    "REGIME_MODEL_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Regime", "model")),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategy"))
import numpy as np, pandas as pd
import fair_value as fv

COMBOS = [("CL", "cal", "WTI"), ("CL", "fly", "WTI"),
          ("CO", "cal", "Brent"), ("CO", "fly", "Brent")]


def _safe(x, fmt="{:.4f}"):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "n/a"
        return fmt.format(x)
    except Exception:
        return "n/a"


def evaluate(product, target, inst):
    print(f"\n=== {inst} {target} ({product}) ===")
    try:
        sig = fv.scored_daily(product, target)
    except Exception as e:
        print("  scored_daily failed:", repr(e)[:140]); return None

    # realized spread column: prefer 'actual', else fair_value+residual
    if "actual" in sig.columns:
        actual = sig["actual"].astype(float)
    elif {"fair_value", "residual"}.issubset(sig.columns):
        actual = (sig["fair_value"] + sig["residual"]).astype(float)
    else:
        print("  no realized-spread column"); return None
    fair = sig["fair_value"].astype(float)

    te = sig[sig["split"] == "test"] if "split" in sig.columns else sig.tail(21)
    idx = te.index
    a = actual.reindex(idx).astype(float)
    f = fair.reindex(idx).astype(float)
    resid = (a - f).dropna()
    mask = a.notna() & f.notna()
    a, f = a[mask], f[mask]
    n = len(a)
    if n < 3:
        print(f"  too few OOS rows ({n})"); return None

    # 1. fit quality
    rmse = float(np.sqrt(((a - f) ** 2).mean()))
    ss_res = float(((a - f) ** 2).sum())
    ss_tot = float(((a - a.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # 2. skill vs random walk (yesterday's realized spread predicts today's)
    a_full = actual.reindex(sig.index).astype(float)
    rw_pred = a_full.shift(1).reindex(idx)[mask]
    rw_err = (a - rw_pred).dropna()
    rmse_rw = float(np.sqrt((rw_err ** 2).mean())) if len(rw_err) else float("nan")
    skill = 1 - rmse / rmse_rw if rmse_rw and rmse_rw == rmse_rw else float("nan")

    # 3. residual bias
    bias = float(resid.mean())
    bias_t = bias / (resid.std(ddof=1) / np.sqrt(len(resid))) if resid.std(ddof=1) > 0 else float("nan")

    # 4. mean-reversion predictive power
    d_next = a_full.shift(-1) - a_full          # next-day change in spread
    r_t = (a_full - fair.reindex(sig.index))     # residual at t (full series)
    j = r_t.reindex(idx)[mask]
    dn = d_next.reindex(idx)[mask]
    both = j.notna() & dn.notna()
    rev_corr = float(np.corrcoef(j[both], dn[both])[0, 1]) if both.sum() > 2 else float("nan")
    # reversion hit-rate: residual>0 should give next-day fall (dn<0)
    hit = ((j[both] > 0) & (dn[both] < 0)) | ((j[both] < 0) & (dn[both] > 0))
    rev_hit = float(hit.mean()) if both.sum() else float("nan")

    # 5. regime usage
    nreg = te["regime_eff"].nunique() if "regime_eff" in te.columns else float("nan")
    ood_frac = float(te["ood"].mean()) if "ood" in te.columns else float("nan")

    print(f"  OOS n={n}  R2={_safe(r2)}  RMSE={_safe(rmse)}  RMSE_naiveRW={_safe(rmse_rw)}  "
          f"skill_vs_RW={_safe(skill)}")
    print(f"  resid_bias={_safe(bias,'{:+.4f}')} (t={_safe(bias_t,'{:+.2f}')})  "
          f"mean|resid|={_safe(resid.abs().mean())}")
    print(f"  reversion corr(resid_t, dSpread_t+1)={_safe(rev_corr,'{:+.3f}')}  "
          f"reversion_hit_rate={_safe(rev_hit,'{:.2f}')}  (>0.5 good)")
    print(f"  regimes_OOS={nreg}  ood_frac={_safe(ood_frac,'{:.2f}')}")

    return dict(inst=inst, target=target, n=n, r2=r2, rmse=rmse, rmse_rw=rmse_rw,
                skill=skill, bias=bias, rev_corr=rev_corr, rev_hit=rev_hit)


def main():
    rows = [r for c in COMBOS if (r := evaluate(*c))]
    if not rows:
        return
    df = pd.DataFrame(rows)
    print("\n=== SUMMARY ===")
    print(df.to_string(index=False,
          formatters={c: (lambda v: _safe(v)) for c in
                      ["r2", "rmse", "rmse_rw", "skill", "bias", "rev_corr", "rev_hit"]}))
    print("\nReadout:")
    print("  skill_vs_RW>0  => model beats a random walk (adds predictive value).")
    print("  resid_bias~0   => no systematic cheap/rich (LONG/SHORT) tilt.")
    print("  rev_corr<0 & rev_hit>0.5 => fair value is a genuine mean-revert attractor.")


if __name__ == "__main__":
    main()
