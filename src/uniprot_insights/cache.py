from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class CacheBackend:
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set(self, key: str, value: Dict[str, Any]) -> None:
        raise NotImplementedError


@dataclass
class InMemoryCache(CacheBackend):
    ttl_seconds: Optional[float] = None
    _store: Dict[str, tuple[float, Dict[str, Any]]] = None

    def __post_init__(self) -> None:
        if self._store is None:
            self._store = {}

    def _is_expired(self, created_at: float) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - created_at) > self.ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        value = self._store.get(key)
        if not value:
            return None
        created_at, payload = value
        if self._is_expired(created_at):
            self._store.pop(key, None)
            return None
        return payload

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = (time.time(), value)


@dataclass
class FileSystemCache(CacheBackend):
    cache_dir: Path
    ttl_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _entry_path(self, key: str) -> Path:
        safe = key.replace("/", "_")
        return self.cache_dir / f"{safe}.json"

    def _is_expired(self, created_at: float) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - created_at) > self.ttl_seconds

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        path = self._entry_path(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                stored = json.load(handle)
            created_at = float(stored.get("created_at", 0))
            payload = stored.get("payload", {})
            if self._is_expired(created_at):
                path.unlink(missing_ok=True)
                return None
            return payload
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, value: Dict[str, Any]) -> None:
        path = self._entry_path(key)
        payload = {"created_at": time.time(), "payload": value}
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
