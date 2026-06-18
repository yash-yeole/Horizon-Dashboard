"""Joint sweep: DIST_D0 (model dispersion) x EXIT (strategy take-profit).
DIST_D0 is read at import from env REGIME_DIST_D0 (one process per value).
EXIT is swept in-process (no cache rebuild). Reports aggregate win-rate + PnL."""
import os, sys, warnings
warnings.filterwarnings("ignore")
os.environ.setdefault(
    "REGIME_MODEL_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Regime", "model")),
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "strategy"))
import fair_value as fv
from backtest import Engine, EngineConfig
from strategy import CalendarMeanReversion

COMBOS = [("CL","cal","WTI"),("CL","fly","WTI"),("CO","cal","Brent"),("CO","fly","Brent")]
EXITS = [0.3, 0.4, 0.5, 0.6]
d0 = os.environ.get("REGIME_DIST_D0", "1.5")

# recompute fair value once for this DIST_D0 (force), keep day_maps in memory
daymaps = {(p,t): fv.daily_fairvalue_map(p, t, force_recompute=True) for p,t,i in COMBOS}

for ex in EXITS:
    tot_pnl = tot_n = 0; w_weighted = 0; per = []
    for p,t,i in COMBOS:
        res = Engine(EngineConfig(product=p, target=t, instrument=i, structure="c1-c2"),
                     strategy=CalendarMeanReversion(exit_=ex), day_map=daymaps[(p,t)]).run()
        s = res["summary"]; n = s.get("n_trades") or 0
        pnl = s.get("net_pnl") or 0.0; wr = s.get("win_rate") or 0.0
        tot_pnl += pnl; tot_n += n; w_weighted += wr * n
        per.append(f"{i[:2]}{t[:1]}:{pnl:+.2f}")
    agg_wr = (w_weighted / tot_n) if tot_n else 0.0
    print(f"DIST_D0={d0} EXIT={ex}: trades={tot_n:3d} winrate={agg_wr:.2f} "
          f"net_pnl={tot_pnl:+.3f}  [{' '.join(per)}]")
