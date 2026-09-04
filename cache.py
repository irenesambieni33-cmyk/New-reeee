"""
RE-ZERO - Cache
Cache simple en mémoire + sur disque (parquet) pour éviter les recalculs
et limiter les appels API répétés.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


class MemoryCache:
    """Cache en mémoire avec TTL (time-to-live) en secondes."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str, ttl_seconds: int = 60) -> Optional[Any]:
        item = self._store.get(key)
        if item is None:
            return None
        timestamp, value = item
        if time.time() - timestamp > ttl_seconds:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def clear(self) -> None:
        self._store.clear()


# Instance globale partagée par l'application
memory_cache = MemoryCache()


def cache_dataframe(key: str, df: pd.DataFrame) -> Path:
    """Sauvegarde un DataFrame OHLCV sur disque (format parquet)."""
    path = CACHE_DIR / f"{key}.parquet"
    df.to_parquet(path)
    return path


def load_cached_dataframe(key: str) -> Optional[pd.DataFrame]:
    path = CACHE_DIR / f"{key}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    return None
