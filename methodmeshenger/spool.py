"""Small durable message spool with explicit delivery states."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping

from .protocol import EnvelopeError, validate_frame


STATES = {"queued", "enroute", "received", "assembled", "expired", "failed"}
TERMINAL_STATES = {"assembled", "expired"}
ALLOWED_TRANSITIONS = {
    "queued": {"enroute", "expired", "failed"},
    "enroute": {"received", "queued", "expired", "failed"},
    "received": {"assembled", "queued", "expired", "failed"},
    "failed": {"queued", "expired"},
    "assembled": set(),
    "expired": set(),
}


class Spool:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self.items: dict[str, dict[str, Any]] = {}
        self._load()

    @staticmethod
    def key(frame: Mapping[str, Any]) -> str:
        return "%s:%s" % (frame["message_id"], frame.get("chunk_index", 0))

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        self.items = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(json.dumps(self.items, indent=2, sort_keys=True), encoding="utf-8")
            temporary.replace(self.path)

    def enqueue(self, frame: Mapping[str, Any], now_ms: int | None = None) -> str:
        validate_frame(frame)
        key = self.key(frame)
        existing = self.items.get(key)
        if existing and existing["state"] in TERMINAL_STATES:
            return key
        self.items[key] = {
            "frame": dict(frame),
            "state": existing["state"] if existing else "queued",
            "attempts": existing.get("attempts", 0) if existing else 0,
            "updated_at_ms": now_ms if now_ms is not None else int(time.time() * 1000),
            "error": existing.get("error") if existing else None,
        }
        self._save()
        return key

    def transition(self, key: str, state: str, *, error: str | None = None, now_ms: int | None = None) -> None:
        if state not in STATES:
            raise EnvelopeError("unknown spool state: " + state)
        if key not in self.items:
            raise EnvelopeError("unknown spool item: " + key)
        current = self.items[key]["state"]
        if state != current and state not in ALLOWED_TRANSITIONS[current]:
            raise EnvelopeError("invalid spool transition: %s -> %s" % (current, state))
        self.items[key]["state"] = state
        self.items[key]["updated_at_ms"] = now_ms if now_ms is not None else int(time.time() * 1000)
        self.items[key]["error"] = error
        if state == "enroute":
            self.items[key]["attempts"] += 1
        self._save()

    def expire_due(self, now_ms: int | None = None) -> list[str]:
        """Mark frames past their sender expiry as expired."""

        now = now_ms if now_ms is not None else int(time.time() * 1000)
        expired = []
        for key, item in self.items.items():
            deadline = int(item["frame"].get("expires_at_ms", 0) or 0)
            if deadline and deadline <= now and item["state"] not in TERMINAL_STATES:
                self.transition(key, "expired", now_ms=now)
                expired.append(key)
        return expired

    def pending(self, recipient: str | None = None) -> list[dict[str, Any]]:
        result = []
        for item in self.items.values():
            if item["state"] not in {"queued", "failed"}:
                continue
            if recipient and item["frame"].get("recipient") != recipient:
                continue
            result.append(item)
        return sorted(result, key=lambda item: item["updated_at_ms"])
