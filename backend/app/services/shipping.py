"""Tanker intelligence from aisstream.io (free real-time AIS over WebSocket).

A background task holds the WebSocket open, filters to oil tankers (AIS ship
type 80-89), and keeps an in-memory store of the latest position per vessel.
The REST endpoints read that store. Cold start is empty and fills over the
first minute as vessels broadcast. No key → consumer stays off (offline state).

Phase 1: live vessels, heatmap, chokepoint counts. Phase 2 (stubs below):
routes, congestion, floating-storage, physical-flow-score — these need
accumulated history / a persistence layer.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from ..config import settings

# ── Regions we subscribe to (lat/lon corners). Chokepoints + major tanker areas. ──
CHOKEPOINTS: dict[str, list[list[float]]] = {
    "Hormuz": [[26.9, 55.8], [25.5, 57.2]],
    "Bab-el-Mandeb": [[13.0, 43.0], [12.3, 43.7]],
    "Suez": [[31.4, 32.2], [29.6, 32.9]],
    "Malacca": [[6.0, 98.5], [1.0, 104.2]],
    "Panama": [[9.7, -80.2], [8.7, -79.3]],
}
# Broader regions to enrich the heatmap (highlighted areas from the spec).
REGIONS: dict[str, list[list[float]]] = {
    "Persian Gulf": [[30.5, 47.0], [23.5, 57.5]],
    "US Gulf": [[30.5, -97.5], [25.0, -88.0]],
    "ARA/Rotterdam": [[52.6, 2.5], [51.0, 4.9]],
    "China East": [[41.0, 117.0], [20.0, 124.0]],
    "West Africa": [[6.5, 0.0], [-6.5, 9.5]],
}

# AIS ship type 80-89 = tanker.
_TANKER_TYPES = set(range(80, 90))


def _classify(loa: float | None) -> str:
    """Rough tanker class from length overall (no DWT in AIS)."""
    if not loa:
        return "Tanker"
    if loa >= 320:
        return "VLCC"
    if loa >= 270:
        return "Suezmax"
    if loa >= 230:
        return "Aframax/LR2"
    if loa >= 200:
        return "LR1"
    if loa >= 160:
        return "MR"
    return "Small"


class _Store:
    """In-memory latest-known state per vessel (keyed by MMSI)."""

    def __init__(self) -> None:
        self.vessels: dict[int, dict[str, Any]] = {}
        self.connected = False
        self.last_msg_at: float = 0.0

    def _v(self, mmsi: int) -> dict[str, Any]:
        return self.vessels.setdefault(mmsi, {"mmsi": mmsi, "type": None, "loa": None})

    def on_static(self, mmsi: int, msg: dict, name: str) -> None:
        v = self._v(mmsi)
        v["type"] = msg.get("Type")
        dim = msg.get("Dimension") or {}
        a, b = dim.get("A") or 0, dim.get("B") or 0
        v["loa"] = (a + b) or v.get("loa")
        v["klass"] = _classify(v["loa"])
        v["destination"] = (msg.get("Destination") or "").strip()
        if name:
            v["name"] = name

    def on_position(self, mmsi: int, msg: dict, meta: dict) -> None:
        v = self._v(mmsi)
        v["lat"] = meta.get("latitude")
        v["lon"] = meta.get("longitude")
        v["sog"] = msg.get("Sog")
        v["cog"] = msg.get("Cog")
        v["heading"] = msg.get("TrueHeading")
        v["name"] = (meta.get("ShipName") or v.get("name") or "").strip()
        v["last_seen"] = time.time()

    def tankers(self) -> list[dict[str, Any]]:
        """Vessels confirmed as tankers with a known position, freshest first."""
        cutoff = time.time() - settings.ais_vessel_ttl
        out = [
            v for v in self.vessels.values()
            if v.get("type") in _TANKER_TYPES and v.get("lat") is not None and v.get("last_seen", 0) > cutoff
        ]
        out.sort(key=lambda v: v.get("last_seen", 0), reverse=True)
        return out

    def prune(self) -> None:
        cutoff = time.time() - settings.ais_vessel_ttl
        for mmsi in [m for m, v in self.vessels.items() if v.get("last_seen", 0) < cutoff and v.get("last_seen")]:
            self.vessels.pop(mmsi, None)


_store = _Store()
_task: asyncio.Task | None = None


def _bounding_boxes() -> list[list[list[float]]]:
    return list(CHOKEPOINTS.values()) + list(REGIONS.values())


async def _run() -> None:
    import websockets  # imported lazily so the app starts even if not installed

    sub = {
        "APIKey": settings.aisstream_api_key,
        "BoundingBoxes": _bounding_boxes(),
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }
    while True:
        try:
            async with websockets.connect(settings.aisstream_url, ping_interval=20, max_size=2**22) as ws:
                await ws.send(json.dumps(sub))
                _store.connected = True
                async for raw in ws:
                    _store.last_msg_at = time.time()
                    try:
                        data = json.loads(raw)
                        meta = data.get("MetaData") or {}
                        mmsi = meta.get("MMSI")
                        body = data.get("Message") or {}
                        if data.get("MessageType") == "PositionReport" and mmsi:
                            _store.on_position(int(mmsi), body.get("PositionReport") or {}, meta)
                        elif data.get("MessageType") == "ShipStaticData" and mmsi:
                            _store.on_static(int(mmsi), body.get("ShipStaticData") or {}, (meta.get("ShipName") or "").strip())
                    except (ValueError, TypeError, KeyError):
                        continue
        except Exception:  # noqa: BLE001 — reconnect on any drop
            _store.connected = False
            await asyncio.sleep(5)


def start() -> None:
    """Launch the consumer if a key is configured (called on app startup)."""
    global _task
    if not settings.aisstream_api_key or _task is not None:
        return
    _task = asyncio.create_task(_run())


def status() -> dict[str, Any]:
    has_key = bool(settings.aisstream_api_key)
    fresh = (time.time() - _store.last_msg_at) < 60 if _store.last_msg_at else False
    return {
        "hasKey": has_key,
        "connected": _store.connected and fresh,
        "vesselCount": len(_store.tankers()),
    }


# ── Query helpers used by the router ──

def vessels(limit: int = 500) -> list[dict[str, Any]]:
    out = []
    for v in _store.tankers()[:limit]:
        out.append({
            "mmsi": v["mmsi"],
            "name": v.get("name") or f"MMSI {v['mmsi']}",
            "klass": v.get("klass") or "Tanker",
            "lat": v["lat"],
            "lon": v["lon"],
            "sog": v.get("sog"),
            "cog": v.get("cog"),
            "heading": v.get("heading"),
            "destination": v.get("destination") or "",
            "lastSeen": int(v.get("last_seen", 0)),
        })
    return out


def heatmap() -> list[list[float]]:
    """[lat, lon, weight] points for the density layer."""
    return [[v["lat"], v["lon"], 1.0] for v in _store.tankers()]


def _in_box(lat: float, lon: float, box: list[list[float]]) -> bool:
    (la1, lo1), (la2, lo2) = box
    return min(la1, la2) <= lat <= max(la1, la2) and min(lo1, lo2) <= lon <= max(lo1, lo2)


# Rough baseline tanker counts per chokepoint for an MVP status (until 7d/30d
# history persistence lands in Phase 2).
_BASELINE: dict[str, int] = {"Hormuz": 25, "Bab-el-Mandeb": 12, "Suez": 15, "Malacca": 30, "Panama": 8}


def chokepoints() -> list[dict[str, Any]]:
    tankers = _store.tankers()
    out = []
    for name, box in CHOKEPOINTS.items():
        count = sum(1 for v in tankers if _in_box(v["lat"], v["lon"], box))
        base = _BASELINE.get(name, 15)
        dev = round((count - base) / base * 100, 1) if base else 0.0
        state = "Congested" if dev >= 40 else "Elevated" if dev >= 15 else "Normal"
        out.append({
            "name": name,
            "count": count,
            "avg7d": None,   # Phase 2: needs history persistence
            "avg30d": None,  # Phase 2
            "baseline": base,
            "deviation": dev,
            "status": state,
        })
    return out
