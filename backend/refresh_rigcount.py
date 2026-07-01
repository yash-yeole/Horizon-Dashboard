"""Regenerate the committed Baker Hughes rig-count seed (backend/seed/rigcount.json).

The deployed backend can't reach Baker Hughes reliably (their site is slow/blocked
from cloud hosts), so it serves this committed snapshot instead of a live fetch.
Run offline on a residential network with a backend venv (httpx + openpyxl), then
commit the updated seed and redeploy:

    python backend/refresh_rigcount.py
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.services import bakerhughes

SEED = Path(__file__).resolve().parent / "seed" / "rigcount.json"


def main() -> None:
    payload = asyncio.run(bakerhughes.fetch_rigcount())
    data = payload.model_dump()
    SEED.parent.mkdir(parents=True, exist_ok=True)
    SEED.write_text(json.dumps(data), encoding="utf-8")
    print(f"wrote {SEED}  (NA {data.get('na_report_date')}, WW {data.get('ww_report_date')})")


if __name__ == "__main__":
    main()
