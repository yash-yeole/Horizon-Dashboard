"""
refresh_fairvalue.py — offline daily fair-value refresh (the ONLY place the
heavy model/sklearn pipeline is invoked).

Run this on a schedule (e.g. once a day, or whenever new DB data lands). It
computes the per-day fair-value map for every product/target the live engine
needs and writes the parquet caches that the API process (app/services/paper.py)
reads. The API never imports the model pipeline itself.

Usage (from backend/):
    .venv\\Scripts\\python.exe refresh_fairvalue.py
    .venv\\Scripts\\python.exe refresh_fairvalue.py --force

The trained model lives in the original Regime project, not in the dashboard.
Point REGIME_MODEL_DIR at it (defaults to the known OneDrive location).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
_STRAT_DIR = os.path.join(HERE, "strategy")

# The model pipeline stays in the Regime project; the vendored strategy/ copy
# only carries the light engine. Let the env var win if already set.
_DEFAULT_MODEL_DIR = os.path.abspath(os.path.join(
    HERE, "..", "..", "..", "Regime", "model"))
os.environ.setdefault("REGIME_MODEL_DIR", _DEFAULT_MODEL_DIR)

if _STRAT_DIR not in sys.path:
    sys.path.insert(0, _STRAT_DIR)

import fair_value  # noqa: E402

# (product, target) pairs backing the four live structures.
COMBOS = [
    ("CL", "cal"),  # WTI c1-c2
    ("CL", "fly"),  # WTI butterfly
    ("CO", "cal"),  # Brent c1-c2
    ("CO", "fly"),  # Brent butterfly
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Refresh daily fair-value caches.")
    ap.add_argument("--force", action="store_true",
                    help="rebuild every cache even if the DB has not advanced")
    args = ap.parse_args()

    model_dir = os.environ["REGIME_MODEL_DIR"]
    if not os.path.isdir(model_dir):
        print(f"ERROR: REGIME_MODEL_DIR does not exist: {model_dir}",
              file=sys.stderr)
        print("Set REGIME_MODEL_DIR to the Regime/model directory.",
              file=sys.stderr)
        return 1
    print(f"REGIME_MODEL_DIR = {model_dir}")

    failures = 0
    for product, target in COMBOS:
        t0 = time.time()
        try:
            fvm = fair_value.daily_fairvalue_map(
                product, target, force_recompute=args.force)
            print(f"  {product}/{target}: {len(fvm)} DB days "
                  f"({time.time() - t0:.1f}s)")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  {product}/{target}: FAILED — {exc}", file=sys.stderr)

    if failures:
        print(f"\nDone with {failures} failure(s).", file=sys.stderr)
        return 1
    print("\nAll fair-value caches refreshed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
