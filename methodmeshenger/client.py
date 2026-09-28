"""Small laptop-side MethodMeshenger client.

The client owns human addressing and delivery state. An ESP node only carries
the already-shaped frame over its radio link.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol

from .directory import Directory
from .protocol import ChunkAssembler, Deduplicator, EnvelopeError, ack_frame, chunk_text, decode_frame, encode_frame
from .spool import Spool


class LineTransport(Protocol):
    def send(self, raw: bytes) -> None: ...


@dataclass
class Delivery:
    key: str
    frame: dict


class Client:
    def __init__(self, *, username: str, device_id: str, directory: Directory, spool: Spool | None = None, transport: LineTransport | None = None) -> None:
        self.username = username.lower()
        self.device_id = device_id
        self.directory = directory
        self.spool = spool or Spool()
        self.transport = transport
        self.received: list[dict] = []
        self.last_error: str | None = None
        self._sequence = 0
        self._dedupe = Deduplicator()
        self._assembler = ChunkAssembler()

    def send_text(self, handle: str, text: str, *, now_ms: int | None = None, inter_chunk_delay_ms: int = 75, wait_for_ack: bool = True, ack_timeout_ms: int = 2000) -> list[Delivery]:
        target = self.directory.resolve(handle)
        if target["type"] != "user":
            raise EnvelopeError("text delivery requires a user handle")
        devices = target["devices"]
        self._sequence += 1
        timestamp = now_ms if now_ms is not None else int(time.time() * 1000)
        deliveries = []
        for index, device_id in enumerate(devices):
            message_id = "%s-%d-%d" % (self.device_id, timestamp, self._sequence + index)
            frames = chunk_text(
                text,
                message_id=message_id,
                conversation_id=self._conversation_id(target["account_id"]),
                sender=self.device_id,
                recipient=device_id,
                created_at_ms=timestamp,
            )
            for frame in frames:
                key = self.spool.enqueue(frame, now_ms=timestamp)
                deliveries.append(Delivery(key, dict(frame)))
                self._transmit(key, frame)
                if wait_for_ack and frame is not frames[-1]:
                    deadline = time.monotonic() + ack_timeout_ms / 1000
                    while self.spool.items[key]["state"] != "received" and time.monotonic() < deadline:
                        time.sleep(0.01)
                if inter_chunk_delay_ms > 0 and frame is not frames[-1]:
                    time.sleep(inter_chunk_delay_ms / 1000)
        return deliveries

    def ingest_line(self, line: bytes | str) -> list[dict]:
        """Consume one JSON event/frame line from the ESP serial console."""

        if isinstance(line, bytes):
            line = line.decode("utf-8", errors="replace")
        line = line.strip()
        if not line:
            return []
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            self.last_error = "invalid serial JSON: %s" % error
            return []
        if not isinstance(record, dict):
            return []
        if record.get("event") == "message" and isinstance(record.get("frame"), dict):
            frame = decode_frame(json.dumps(record["frame"]))
            self._send_ack(frame)
            if not self._dedupe.accept(frame):
                return []
            assembled = self._assembler.add(frame)
            if assembled is None:
                return []
            delivered = dict(frame)
            delivered["payload"] = assembled
            delivered["assembled"] = True
            self.received.append(delivered)
            return [delivered]
        if record.get("event") == "ack_received" and isinstance(record.get("frame"), dict):
            frame = decode_frame(json.dumps(record["frame"]))
            try:
                payload = json.loads(frame["payload"])
                self._mark_acknowledged(payload["ack_for"])
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                self.last_error = "invalid acknowledgement: %s" % error
            return []
        if record.get("event") == "error":
            self.last_error = str(record.get("detail", "serial error"))
        return []

    def retry_pending(self) -> int:
        count = 0
        for item in self.spool.pending():
            self._transmit(item["key"] if "key" in item else self.spool.key(item["frame"]), item["frame"])
            count += 1
        return count

    def retry_due(self, *, now_ms: int, retry_after_ms: int = 5000) -> int:
        count = 0
        for key, item in self.spool.retryable(now_ms, retry_after_ms):
            if item["state"] == "enroute":
                self.spool.transition(key, "queued", now_ms=now_ms)
            self._transmit(key, item["frame"])
            count += 1
        return count

    def _conversation_id(self, account_id: str) -> str:
        return "%s:%s" % (self.username, account_id)

    def _transmit(self, key: str, frame: dict) -> None:
        if self.transport is None:
            return
        self.spool.transition(key, "enroute")
        self.transport.send(encode_frame(frame) + b"\n")

    def _send_ack(self, frame: dict) -> None:
        if self.transport is None:
            return
        ack = ack_frame(
            ack_for=frame["message_id"],
            sender=self.device_id,
            recipient=frame["sender"],
            status="received",
            conversation_id=frame.get("conversation_id", ""),
        )
        self.transport.send(encode_frame(ack) + b"\n")

    def _mark_acknowledged(self, message_id: str) -> None:
        for key, item in self.spool.items.items():
            if item["frame"].get("message_id") == message_id and item["state"] == "enroute":
                self.spool.transition(key, "received")
