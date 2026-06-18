"""
data_feed.py — market-data access for the paper-trading / backtest engine.

One engine, two data taps:
  * BacktestFeed — iterate historical 15-min bars from the strategy/files/*.db files
  * LiveFeed     — poll the latest bars from the same DB while it is being appended

Both expose the SAME interface (a stream of timestamped spread observations), so the
strategy / lifecycle / accounting core never knows whether it is back-testing or live.

DB layout (see strategy/files/README.md):
  * one .db per trading day:  bars_15min_YYYYMMDD.db
  * one table per contract:   {PRODUCT}_{TENOR}  e.g. CL_N26, CO_N26
  * schema: timestamp TEXT (UTC, bar-open), open, high, low, close, volume
"""
from __future__ import annotations
import glob
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

# Where the bar DB files live. Defaults to the local (OneDrive-synced) copy, but
# can be pointed at the live source drive to avoid OneDrive sync lag / file flicker:
#   * set env var  REGIME_DATA_DIR=I:\Public\Siddharth Raj\lightstreamer_data
#   * or call  set_data_dir(path)  at runtime
# The live source is preferable for real-time use; the OneDrive copy is a laggy mirror.
_DEFAULT_FILES_DIR = os.path.join(HERE, "files")
# Default to the live source if reachable, otherwise fall back to the local copy.
# Override at any time via env var REGIME_DATA_DIR or call set_data_dir(path).
_LIVE_SOURCE_DEFAULT = r"I:\Public\Summer Interns Energy\DB"
FILES_DIR = os.environ.get(
    "REGIME_DATA_DIR",
    _LIVE_SOURCE_DEFAULT if os.path.isdir(_LIVE_SOURCE_DEFAULT) else _DEFAULT_FILES_DIR
)
# Live source drive (confirmed reachable 2026-06-16; immutable=1 required — WAL
# locking doesn't work over SMB network shares but the main .db is readable).
LIVE_SOURCE_DIR = r"I:\Public\Summer Interns Energy\DB"


def set_data_dir(path: str) -> str:
    """Point the feed at a different folder of bars_15min_*.db files (e.g. the live
    source drive). Returns the resolved path. Pass None/'' to reset to default."""
    global FILES_DIR
    FILES_DIR = path or _DEFAULT_FILES_DIR
    return FILES_DIR


def use_live_source(verbose: bool = True) -> str:
    """Switch to the documented live source drive if it is reachable, else stay put."""
    if os.path.isdir(LIVE_SOURCE_DIR):
        if verbose:
            print(f"data_feed: using LIVE source {LIVE_SOURCE_DIR}")
        return set_data_dir(LIVE_SOURCE_DIR)
    if verbose:
        print(f"data_feed: live source {LIVE_SOURCE_DIR} not reachable; "
              f"keeping {FILES_DIR}")
    return FILES_DIR

# month code -> calendar month (futures convention)
MONTH_CODE = {"F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
              "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12}
# product code in the DB -> our instrument label
PRODUCT_LABEL = {"CL": "WTI", "CO": "Brent"}


# --------------------------------------------------------------------- discovery
def list_db_files(files_dir: str | None = None) -> list[str]:
    """All bar DB files sorted by date ascending. Resolves FILES_DIR at call time so
    set_data_dir()/use_live_source() take effect."""
    fs = glob.glob(os.path.join(files_dir or FILES_DIR, "bars_15min_*.db"))
    return sorted(fs)


def latest_db_file(files_dir: str | None = None) -> str:
    fs = list_db_files(files_dir)
    if not fs:
        raise FileNotFoundError(f"no bars_15min_*.db in {files_dir}")
    return fs[-1]


def _wal_state(db_path: str) -> tuple[bool, bool]:
    """(-wal present & non-empty, -shm present)."""
    wal = os.path.exists(db_path + "-wal") and os.path.getsize(db_path + "-wal") > 0
    shm = os.path.exists(db_path + "-shm")
    return wal, shm


# paths confirmed to be network shares (cached after first probe so we don't retry
# the local-open strategies on every call).
_NETWORK_PATHS: set[str] = set()

# Local mirror dir for network DBs: we copy the main .db + -wal here so SQLite can
# REPLAY the WAL (impossible to read directly over SMB, where WAL locking is
# unavailable).  This is what lets the backtest see the freshest in-flight prices
# that live only in the -wal file, not yet checkpointed into the main .db.
_MIRROR_DIR = os.path.join(tempfile.gettempdir(), "regime_db_mirror")


def _mirror_with_wal(db_path: str) -> str:
    """Copy the network DB (.db + -wal) to a local mirror and return the local path.

    SQLite applies the WAL automatically when the local copy is opened, so ALL
    in-flight rows become visible.  Re-copies only when the source .db/-wal size or
    mtime changes, so repeated reads within a poll are cheap.  Any stale local -shm
    is removed so SQLite rebuilds its WAL index cleanly from the copied -wal.
    """
    os.makedirs(_MIRROR_DIR, exist_ok=True)
    local = os.path.join(_MIRROR_DIR, os.path.basename(db_path))

    def _sig(p: str):
        try:
            st = os.stat(p)
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    src_sig = repr((_sig(db_path), _sig(db_path + "-wal")))
    meta = local + ".srcsig"
    cur_sig = None
    if os.path.exists(meta):
        try:
            with open(meta, "r") as f:
                cur_sig = f.read()
        except OSError:
            pass

    if cur_sig != src_sig or not os.path.exists(local):
        shutil.copy2(db_path, local)                       # main .db
        wal_src = db_path + "-wal"
        if os.path.exists(wal_src) and os.path.getsize(wal_src) > 0:
            shutil.copy2(wal_src, local + "-wal")           # in-flight rows
        elif os.path.exists(local + "-wal"):
            os.remove(local + "-wal")
        # drop any stale shm so SQLite rebuilds the WAL index from the copied -wal
        if os.path.exists(local + "-shm"):
            os.remove(local + "-shm")
        with open(meta, "w") as f:
            f.write(src_sig)
    return local


def _connect(db_path: str) -> sqlite3.Connection:
    """Open the DB so that ALL readable rows are visible (incl. in-flight WAL rows).

    Local / WAL-capable paths open read-only directly.  Network/SMB shares (where
    WAL locking is unavailable) are mirrored locally first so the -wal is replayed
    and the freshest prices are included — never skipped.  A path is probed once,
    then its network status is cached so repeat calls go straight to the right path.
    """
    if db_path in _NETWORK_PATHS:
        return sqlite3.connect(_mirror_with_wal(db_path), timeout=10)

    # strategy 1: read-only (preferred for local / WAL-capable paths)
    conn = None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=10)
        conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
        return conn
    except sqlite3.DatabaseError:
        if conn:
            try: conn.close()
            except Exception: pass

    # strategy 2: wal-without-shm on a local path (OneDrive mid-sync)
    wal, shm = _wal_state(db_path)
    if wal and not shm:
        try:
            conn = sqlite3.connect(db_path, timeout=10)
            conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
            return conn
        except sqlite3.DatabaseError:
            if conn:
                try: conn.close()
                except Exception: pass

    # strategy 3: network path — mirror .db + -wal locally and replay the WAL so the
    # latest in-flight prices are INCLUDED (previously these rows were skipped).
    import time
    _NETWORK_PATHS.add(db_path)
    wal, _ = _wal_state(db_path)
    print(f"data_feed: {os.path.basename(db_path)} — network path detected, "
          f"mirroring .db+-wal locally to INCLUDE in-flight WAL rows"
          + ("" if wal else " (no -wal present)"))
    for attempt in range(3):
        try:
            local = _mirror_with_wal(db_path)
            conn = sqlite3.connect(local, timeout=10)
            conn.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()
            return conn
        except sqlite3.DatabaseError:
            if attempt < 2:
                time.sleep(0.5)
    raise sqlite3.DatabaseError(
        f"database disk image is malformed after 3 attempts: {db_path}"
    )


def list_contracts(db_path: str, product: str | None = None) -> list[str]:
    """Table names, optionally filtered to one product code (CL / CO)."""
    with _connect(db_path) as c:
        tabs = [r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    if product:
        tabs = [t for t in tabs if t.startswith(product + "_")]
    return tabs


def _expiry(tenor: str) -> pd.Timestamp:
    """Approx expiry from tenor code e.g. 'N26' -> 2026-07 (day-1 placeholder)."""
    m = re.match(r"^([FGHJKMNQUVXZ])(\d{2})$", tenor)
    if not m:
        return pd.NaT
    return pd.Timestamp(year=2000 + int(m.group(2)), month=MONTH_CODE[m.group(1)], day=1)


def read_contract(db_path: str, table: str) -> pd.DataFrame:
    """OHLCV for one contract table, indexed by UTC timestamp."""
    with _connect(db_path) as c:
        df = pd.read_sql(f'SELECT * FROM "{table}" ORDER BY timestamp',
                         c, parse_dates=["timestamp"]).set_index("timestamp")
    return df


# ------------------------------------------------------------- curve / roll map
def front_tenors(db_path: str, product: str, n: int = 2,
                 as_of: pd.Timestamp | None = None) -> list[str]:
    """The n nearest-expiry tenors for a product that have data, sorted by expiry.

    Returns tenor codes (e.g. ['N26','Q26']).  Front month = c1, next = c2, ...
    Contracts already past expiry (relative to as_of) are skipped.
    """
    tabs = list_contracts(db_path, product)
    tenors = [t.split("_", 1)[1] for t in tabs]
    rows = [(t, _expiry(t)) for t in tenors]
    rows = [(t, e) for t, e in rows if pd.notna(e)]
    if as_of is not None:
        # keep contracts whose expiry month is >= as_of month (front-month still trading)
        rows = [(t, e) for t, e in rows if e >= as_of.normalize().replace(day=1)]
    rows.sort(key=lambda x: x[1])
    return [t for t, _ in rows[:n]]


def spread_series(db_path: str, product: str, leg1: str, leg2: str,
                  field: str = "close") -> pd.DataFrame:
    """Aligned spread = leg1 - leg2 from two contract tables of one product.

    Returns a DataFrame indexed by timestamp with columns:
      c1, c2, spread, plus c1/c2 OHLC if needed downstream.
    """
    t1, t2 = f"{product}_{leg1}", f"{product}_{leg2}"
    a = read_contract(db_path, t1)
    b = read_contract(db_path, t2)
    out = pd.DataFrame({
        "c1": a[field], "c2": b[field],
        "c1_high": a["high"], "c1_low": a["low"],
        "c2_high": b["high"], "c2_low": b["low"],
    })
    out = out.dropna(subset=["c1", "c2"])
    out["spread"] = out["c1"] - out["c2"]
    out.attrs["product"] = product
    out.attrs["leg1"] = leg1
    out.attrs["leg2"] = leg2
    return out


def calendar_spread(db_path: str, product: str = "CL",
                    field: str = "close", as_of: pd.Timestamp | None = None) -> pd.DataFrame:
    """Convenience: front c1-c2 calendar spread for a product from one DB file."""
    legs = front_tenors(db_path, product, n=2, as_of=as_of)
    if len(legs) < 2:
        raise ValueError(f"need 2 front tenors for {product}, got {legs}")
    df = spread_series(db_path, product, legs[0], legs[1], field=field)
    return df


# ------------------------------------------------------------------ Bar record
@dataclass
class Bar:
    ts: pd.Timestamp
    instrument: str          # e.g. "WTI"
    structure: str           # e.g. "c1-c2"
    spread: float
    c1: float
    c2: float
    leg1: str
    leg2: str


def _bars_from_frame(df: pd.DataFrame, instrument: str, structure: str) -> list[Bar]:
    leg1, leg2 = df.attrs.get("leg1", ""), df.attrs.get("leg2", "")
    return [Bar(ts=ts, instrument=instrument, structure=structure,
                spread=float(r.spread), c1=float(r.c1), c2=float(r.c2),
                leg1=leg1, leg2=leg2)
            for ts, r in df.iterrows()]


# ----------------------------------------------------------------- BacktestFeed
class BacktestFeed:
    """Iterate historical c1-c2 spread bars across all DB files for one product."""

    def __init__(self, product: str = "CL", instrument: str | None = None,
                 structure: str = "c1-c2", files_dir: str | None = None,
                 field: str = "close"):
        self.product = product
        self.instrument = instrument or PRODUCT_LABEL.get(product, product)
        self.structure = structure
        self.files_dir = files_dir          # None -> resolve FILES_DIR at call time
        self.field = field

    def frame(self) -> pd.DataFrame:
        """Concatenated spread frame across all DB files, deduped by timestamp."""
        parts = []
        for db in list_db_files(self.files_dir):
            try:
                # use the file's own date to choose the front tenor at that time
                as_of = _date_from_path(db)
                parts.append(calendar_spread(db, self.product, self.field, as_of))
            except Exception as e:  # noqa: BLE001
                print(f"skip {os.path.basename(db)}: {e!r}")
        if not parts:
            return pd.DataFrame()
        out = pd.concat(parts)
        out = out[~out.index.duplicated(keep="last")].sort_index()
        out.attrs["product"] = self.product
        # leg attrs from the last file
        if parts:
            out.attrs["leg1"] = parts[-1].attrs.get("leg1", "")
            out.attrs["leg2"] = parts[-1].attrs.get("leg2", "")
        return out

    def __iter__(self):
        df = self.frame()
        for b in _bars_from_frame(df, self.instrument, self.structure):
            yield b


# --------------------------------------------------------------------- LiveFeed
class LiveFeed:
    """Poll the latest bars from the newest DB file (which a collector is appending).

    Same Bar interface as BacktestFeed.  `poll()` returns only bars newer than the
    last one already seen, so a dashboard loop can call it on a timer.
    """

    def __init__(self, product: str = "CL", instrument: str | None = None,
                 structure: str = "c1-c2", files_dir: str | None = None,
                 field: str = "close"):
        self.product = product
        self.instrument = instrument or PRODUCT_LABEL.get(product, product)
        self.structure = structure
        self.files_dir = files_dir          # None -> resolve FILES_DIR at call time
        self.field = field
        self._last_ts: pd.Timestamp | None = None

    def snapshot(self) -> pd.DataFrame:
        db = latest_db_file(self.files_dir)
        return calendar_spread(db, self.product, self.field, _date_from_path(db))

    def poll(self) -> list[Bar]:
        df = self.snapshot()
        if self._last_ts is not None:
            df = df[df.index > self._last_ts]
        if not df.empty:
            self._last_ts = df.index[-1]
        return _bars_from_frame(df, self.instrument, self.structure)


def _date_from_path(db_path: str) -> pd.Timestamp:
    m = re.search(r"bars_15min_(\d{8})", os.path.basename(db_path))
    return pd.Timestamp(m.group(1)) if m else pd.NaT


if __name__ == "__main__":
    fs = list_db_files()
    print(f"{len(fs)} DB file(s):", [os.path.basename(f) for f in fs])
    feed = BacktestFeed("CL")
    df = feed.frame()
    print(f"WTI c1-c2: {len(df)} bars  legs={df.attrs.get('leg1')}-{df.attrs.get('leg2')}")
    print(df[["c1", "c2", "spread"]].head())
    print(df[["c1", "c2", "spread"]].tail())
