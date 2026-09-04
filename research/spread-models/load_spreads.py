"""Data layer: load Brent (LCO) minute data and build daily calendar-spread series.

Convention (standard): positive spread = backwardation.
  M1-M2 = c1 - c2
  M2-M4 = c2 - c4
  M1-M6 = c1 - c6

Continuous nth-nearby columns are used directly (c1..c6 weighted mids). We resample
the 1-minute grid to one snapshot per UTC trading day (last valid print of the day),
which removes intraday microstructure noise and gives a clean weekly-change study.
"""
from __future__ import annotations

import os
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "Regime", "data")
LCO_FILE = os.path.join(DATA_DIR, "LCO_data.csv")

# Mid columns for the first six nearbys, per the header layout
#   timestamp, c1||contract, c1||weighted_mid, c2||contract, c2||weighted_mid, ...
MID_COLS = {f"c{i}": f"c{i}||weighted_mid" for i in range(1, 7)}

SPREAD_DEFS = {
    "M1-M2": ("c1", "c2"),
    "M2-M4": ("c2", "c4"),
    "M1-M6": ("c1", "c6"),
}


def load_daily_spreads(path: str = LCO_FILE) -> pd.DataFrame:
    """Return a daily DataFrame indexed by date with the three spread series."""
    usecols = ["timestamp"] + list(MID_COLS.values())
    df = pd.read_csv(path, skiprows=1, usecols=usecols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")

    # rename mid columns to c1..c6
    df = df.rename(columns={v: k for k, v in MID_COLS.items()})

    # daily snapshot: last valid print per UTC date for each nearby
    df["date"] = df["timestamp"].dt.date
    daily = df.groupby("date")[list(MID_COLS.keys())].last()
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()

    out = pd.DataFrame(index=daily.index)
    for name, (a, b) in SPREAD_DEFS.items():
        out[name] = daily[a] - daily[b]

    # keep business-day-like rows: drop fully empty rows
    out = out.dropna(how="all")
    return out


if __name__ == "__main__":
    s = load_daily_spreads()
    print("rows:", len(s), "from", s.index.min().date(), "to", s.index.max().date())
    print(s.describe().round(3))
    print("\nJune 2025 Israel-Iran analog window:")
    print(s.loc["2025-06-10":"2025-06-27"].round(3))
