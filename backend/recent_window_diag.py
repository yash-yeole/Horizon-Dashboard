"""PHASE A.2 — why did z compress in the LIVE tail? (read-only)

Walk-forward showed the model is historically fine (z over-dispersed if anything).
The no-trades symptom is recent. Decompose the live test rows to see whether the
recent compression is driven by:
  (a) DENOMINATOR inflation: feat_dist/DIST_D0 widening resid_std right now, or
  (b) NUMERATOR collapse:    spread sitting close to (or biased vs) fair value.

make_signals overwrites resid_std_train with the INFLATED value
(infl = max(1, feat_dist/DIST_D0)); we back out the raw per-regime std as
raw = inflated / infl, so we can see how much inflation alone is shrinking z.
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
DIST_D0 = float(os.environ.get("REGIME_DIST_D0", 1.1))


def report(product, target, instrument):
    print(f"\n=== {instrument} {target} ({product}) ===")
    try:
        sig = fv.scored_daily(product, target)
    except Exception as e:
        print("  failed:", repr(e)[:120]); return
    te = sig[sig["split"] == "test"].copy() if "split" in sig else sig.tail(21).copy()
    if te.empty:
        print("  no test rows"); return
    fd = te["feat_dist"].astype(float) if "feat_dist" in te else pd.Series(np.nan, index=te.index)
    infl = np.maximum(1.0, fd / DIST_D0)
    inflated_std = te["resid_std_train"].astype(float)
    raw_std = inflated_std / infl
    resid = te["residual"].astype(float)
    z = te["z"].astype(float)
    # what z WOULD be without inflation
    z_raw = resid / raw_std.replace(0, np.nan)

    print(f"  test rows={len(te)}  span {te.index.min().date()}..{te.index.max().date()}")
    print(f"  feat_dist  mean={fd.mean():.2f} max={fd.max():.2f}  "
          f"=> inflation mean={infl.mean():.2f} max={infl.max():.2f}")
    print(f"  raw_std mean={raw_std.mean():.3f}  inflated_std mean={inflated_std.mean():.3f}")
    print(f"  residual   mean={resid.mean():+.3f}  std={resid.std(ddof=1):.3f}  "
          f"|mean|/std={abs(resid.mean())/ (resid.std(ddof=1) or np.nan):.2f}")
    print(f"  z (inflated)  mean={z.mean():+.2f} mean|z|={z.abs().mean():.2f} max|z|={z.abs().max():.2f}")
    print(f"  z (no inflat) mean={z_raw.mean():+.2f} mean|z|={z_raw.abs().mean():.2f} max|z|={z_raw.abs().max():.2f}")
    crossed = (z.abs() >= 1).mean(); crossed_raw = (z_raw.abs() >= 1).mean()
    print(f"  %days |z|>=1  inflated={crossed:.0%}  no-inflation={crossed_raw:.0%}")
    regs = te["regime_eff"].value_counts().to_dict() if "regime_eff" in te else {}
    print(f"  regimes in tail: {regs}")


def main():
    for c in COMBOS:
        report(*c)
    print("\nREAD: if 'no-inflation' z crosses 1 much more often than 'inflated', the "
          "feat_dist/DIST_D0 widening is the proximate cause of the no-trades.\n"
          "If both are low, the numerator (spread near/biased vs fair) is the cause.")


if __name__ == "__main__":
    main()
