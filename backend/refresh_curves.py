"""Generate committed forward-curve snapshots for the dashboard.

The large raw 1-min feeds live in Regime/data/<PROD>_data.csv (OneDrive, ~500 MB
each, gitignored). This resamples each to one settle per UTC trading day (last
valid weighted-mid per contract) and writes a small snapshot into
backend/curves/<name>_settle.csv. Those snapshots ARE committed, so the deployed
dashboard (GitHub / Hugging Face) still renders the forward curves — static, from
the last snapshot — even though the raw feeds never leave the local machine.

Layout matches the shipped ICE settle CSVs the curve service already reads
(row 0 = contract codes, row 1 = Timestamp/SETTLE labels, then newest-first rows).
Prices stay in each feed's native unit (no bbl/tonne conversion here).

Products: LCO->brent, LGO->gasoil. These are the ICE curves that aren't on Yahoo,
so they ship as snapshots; WTI/Heating Oil/RBOB are live-from-Yahoo in
app/services/curve.py and need no snapshot.

Run offline whenever you want to refresh the shipped curves (any venv with pandas):
    python backend/refresh_curves.py            # all products
    python backend/refresh_curves.py LCO        # a subset
Override paths via env: CURVES_DATA_DIR (input dir) / CURVES_OUT_DIR (output dir).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

BACKEND = Path(__file__).resolve().parent
ROOT = BACKEND.parent
DATA_DIR = Path(os.environ.get("CURVES_DATA_DIR", ROOT / "Regime" / "data"))
OUT_DIR = Path(os.environ.get("CURVES_OUT_DIR", BACKEND / "curves"))

# raw product code -> snapshot name (the curve id used in app/services/curve.py)
PRODUCTS: dict[str, str] = {
    "LCO": "brent",
    "LGO": "gasoil",
}


def _header(path: Path) -> tuple[int, list[str]]:
    """Return (rows_to_skip, columns). Row 0 may be a '#meta:' comment line."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        first = fh.readline()
    skip = 1 if first.lstrip().startswith("#") else 0
    cols = pd.read_csv(path, skiprows=skip, nrows=0).columns.tolist()
    return skip, cols


def build(code: str) -> None:
    src = DATA_DIR / f"{code}_data.csv"
    if not src.is_file():
        print(f"[skip] {code}: source not found ({src})", flush=True)
        return

    skip, cols = _header(src)
    mid_cols = [c for c in cols if c.endswith("||weighted_mid")]
    if not mid_cols:
        print(f"[skip] {code}: no '||weighted_mid' columns in header", flush=True)
        return
    ts_col = "timestamp" if "timestamp" in cols else cols[0]

    mb = src.stat().st_size / 1e6
    print(f"[{code}] reading {src.name}  ({mb:.0f} MB, {len(mid_cols)} contracts) …", flush=True)
    # usecols keeps memory sane on the ~500 MB feeds: only timestamp + the mids.
    df = pd.read_csv(src, skiprows=skip, usecols=[ts_col] + mid_cols)
    df[ts_col] = pd.to_datetime(df[ts_col], utc=True, format="mixed")
    df["date"] = df[ts_col].dt.date

    # daily snapshot: last valid print per UTC date for each nearby contract
    daily = df.groupby("date")[mid_cols].last().sort_index().dropna(how="all")
    if daily.empty:
        print(f"[skip] {code}: no daily rows after resample", flush=True)
        return

    n = len(mid_cols)
    # The code/label rows are cosmetic — curve.py reads (date, value) pairs
    # positionally — so we just number the contracts c1..cN.
    codes = ",".join(f"{code}c{i},{code}c{i}" for i in range(1, n + 1))
    labels = ",".join(["Timestamp,SETTLE"] * n)

    lines = [codes, labels]
    for d, row in daily.sort_index(ascending=False).iterrows():  # newest-first
        ds = pd.Timestamp(d).strftime("%d-%m-%y")
        cells: list[str] = []
        for c in mid_cols:
            v = row[c]
            cells.append(ds)
            cells.append("" if pd.isna(v) else f"{v:.2f}")
        lines.append(",".join(cells))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{PRODUCTS[code]}_settle.csv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    lo, hi = daily.index.min(), daily.index.max()
    sample = ", ".join(f"{daily.iloc[-1][c]:.2f}" for c in mid_cols[:4])
    print(f"[ok] {code} -> {out.name}  ({len(daily)} days x {n} contracts, "
          f"{lo} -> {hi}); latest M1-M4: {sample}", flush=True)


def main() -> None:
    codes = [a.upper() for a in sys.argv[1:]] or list(PRODUCTS)
    unknown = [c for c in codes if c not in PRODUCTS]
    if unknown:
        raise SystemExit(f"unknown product(s): {unknown}. Known: {list(PRODUCTS)}")
    for c in codes:
        build(c)


if __name__ == "__main__":
    main()
