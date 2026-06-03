import time
from typing import Any


class TTLCache:
    """Minimal in-memory TTL cache. Suitable for a single-process dev/proxy server."""

    def __init__(self, ttl: float) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            return None
        return value

    def get_stale(self, key: str) -> Any | None:
        """Return a value even if expired (used as a fallback when upstream fails)."""
        entry = self._store.get(key)
        return entry[1] if entry else None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time() + self._ttl, value)
