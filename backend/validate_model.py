"""Walk-forward validation: residual quality + z-calibration + backtest PnL.
Run with SYSTEM python (needs sklearn) and REGIME_MODEL_DIR set."""
import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault(
    "REGIME_MODEL_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Regime", "model")),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategy"))
import numpy as np, pandas as pd
import fair_value as fv
from backtest import Engine, EngineConfig

COMBOS = [("CL","cal","WTI"),("CL","fly","WTI"),("CO","cal","Brent"),("CO","fly","Brent")]

def main():
    for product, target, inst in COMBOS:
        print(f"\n=== {inst} {target} ({product}) ===")
        try:
            sig = fv.scored_daily(product, target)
        except Exception as e:
            print("  scored_daily failed:", repr(e)[:120]); continue
        te = sig[sig["split"] == "test"] if "split" in sig else sig.tail(21)
        resid = te["residual"].dropna()
        rmse = float(np.sqrt((resid**2).mean())) if len(resid) else float("nan")
        z = te["z"].dropna()
        print(f"  OOS rows={len(te)}  resid_RMSE={rmse:.4f}  "
              f"mean|z|={z.abs().mean():.2f}  max|z|={z.abs().max():.2f}  "
              f"frac|z|>2={ (z.abs()>2).mean():.2f}")
        if "feat_dist" in te.columns:
            print(f"  feat_dist: mean={te['feat_dist'].mean():.2f} max={te['feat_dist'].max():.2f}")
        try:
            res = Engine(EngineConfig(product=product, target=target,
                         instrument=inst, structure="c1-c2")).run()
            s = res["summary"]
            wr = s.get('win_rate'); pnl = s.get('net_pnl'); pf = s.get('profit_factor')
            wr_s = f"{wr:.2f}" if wr is not None else "n/a"
            pnl_s = f"{pnl:.3f}" if pnl is not None else "n/a"
            pf_s = f"{pf:.3f}" if pf is not None else "n/a"
            print(f"  BT trades={s.get('n_trades')} win={wr_s} net_pnl={pnl_s} pf={pf_s} exits={s.get('exit_reasons')}")
        except Exception as e:
            print("  backtest failed:", repr(e)[:120])

if __name__ == "__main__":
    main()
