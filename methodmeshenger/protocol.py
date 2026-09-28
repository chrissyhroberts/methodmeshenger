"""Reference MethodMeshenger v1 envelope implementation.

This module is deliberately dependency-free. It is the reference behaviour
for the laptop client and protocol tests; constrained firmware may implement
the same field order and validation rules independently.
"""

from __future__ import annotations

import binascii
import json
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping


PROTOCOL = "methodmeshenger"
VERSION = 1
CRC_FIELDS = (
    "version",
    "message_id",
    "conversation_id",
    "sender",
    "recipient",
    "kind",
    "encoding",
    "sequence",
    "chunk_index",
    "chunk_count",
    "created_at_ms",
    "expires_at_ms",
    "ttl",
    "metadata",
    "payload",
)
SUPPORTED_KINDS = {"text", "attachment", "voice", "ack", "control"}


class EnvelopeError(ValueError):
    """Raised when a frame is malformed or fails integrity validation."""


def _value(frame: Mapping[str, Any], field: str) -> str:
    value = frame.get(field, "")
    if value is None:
        return ""
    return str(value)


def canonical_bytes(frame: Mapping[str, Any]) -> bytes:
    """Return the stable, order-independent CRC input for a frame."""

    return "|".join(_value(frame, field) for field in CRC_FIELDS).encode("utf-8")


def crc32(frame: Mapping[str, Any]) -> str:
    return "%08x" % (binascii.crc32(canonical_bytes(frame)) & 0xFFFFFFFF)


def _base_frame(
    *,
    message_id: str,
    conversation_id: str,
    sender: str,
    recipient: str,
    kind: str,
    encoding: str,
    sequence: int,
    chunk_index: int,
    chunk_count: int,
    payload: str,
    metadata: str = "",
    created_at_ms: int = 0,
    expires_at_ms: int = 0,
    ttl: int = 1,
) -> OrderedDict:
    frame = OrderedDict(
        (
            ("protocol", PROTOCOL),
            ("version", VERSION),
            ("message_id", message_id),
            ("conversation_id", conversation_id),
            ("sender", sender),
            ("recipient", recipient),
            ("kind", kind),
            ("encoding", encoding),
            ("sequence", sequence),
            ("chunk_index", chunk_index),
            ("chunk_count", chunk_count),
            ("created_at_ms", created_at_ms),
            ("expires_at_ms", expires_at_ms),
            ("ttl", ttl),
            ("metadata", metadata),
            ("payload", payload),
        )
    )
    frame["crc32"] = crc32(frame)
    return frame


def chunk_text(
    text: str,
    *,
    message_id: str,
    conversation_id: str,
    sender: str,
    recipient: str,
    sequence: int = 1,
    max_chunk_chars: int = 120,
    created_at_ms: int = 0,
    expires_at_ms: int = 0,
    ttl: int = 1,
) -> list[OrderedDict]:
    """Create deterministic UTF-8 text frames with bounded payloads."""

    if not message_id or not sender or not recipient:
        raise EnvelopeError("message_id, sender and recipient are required")
    if max_chunk_chars < 1:
        raise EnvelopeError("max_chunk_chars must be positive")
    chunks = [text[i : i + max_chunk_chars] for i in range(0, len(text), max_chunk_chars)] or [""]
    return [
        _base_frame(
            message_id=message_id,
            conversation_id=conversation_id,
            sender=sender,
            recipient=recipient,
            kind="text",
            encoding="utf-8",
            sequence=sequence,
            chunk_index=index,
            chunk_count=len(chunks),
            payload=chunk,
            metadata="",
            created_at_ms=created_at_ms,
            expires_at_ms=expires_at_ms,
            ttl=ttl,
        )
        for index, chunk in enumerate(chunks)
    ]


def chunk_content(
    payload: str,
    *,
    kind: str,
    encoding: str,
    metadata: str,
    message_id: str,
    conversation_id: str,
    sender: str,
    recipient: str,
    sequence: int = 1,
    max_chunk_chars: int = 120,
    created_at_ms: int = 0,
    expires_at_ms: int = 0,
    ttl: int = 1,
) -> list[OrderedDict]:
    """Build chunks for opaque attachment, voice, or encrypted content.

    ``metadata`` is a compact JSON string whose schema belongs to the client.
    Keeping it in the signed/integrity-protected envelope means a receiver can
    describe a file or recording without asking the ESP node to understand it.
    """

    if kind not in {"attachment", "voice", "control"}:
        raise EnvelopeError("chunk_content does not support kind: " + kind)
    if not message_id or not sender or not recipient:
        raise EnvelopeError("message_id, sender and recipient are required")
    if not isinstance(metadata, str):
        raise EnvelopeError("metadata must be a compact JSON string")
    if max_chunk_chars < 1:
        raise EnvelopeError("max_chunk_chars must be positive")
    chunks = [payload[i : i + max_chunk_chars] for i in range(0, len(payload), max_chunk_chars)] or [""]
    return [
        _base_frame(
            message_id=message_id,
            conversation_id=conversation_id,
            sender=sender,
            recipient=recipient,
            kind=kind,
            encoding=encoding,
            sequence=sequence,
            chunk_index=index,
            chunk_count=len(chunks),
            metadata=metadata,
            payload=chunk,
            created_at_ms=created_at_ms,
            expires_at_ms=expires_at_ms,
            ttl=ttl,
        )
        for index, chunk in enumerate(chunks)
    ]


def ack_frame(
    *,
    ack_for: str,
    sender: str,
    recipient: str,
    status: str,
    conversation_id: str = "",
    sequence: int = 1,
) -> OrderedDict:
    """Create a small application acknowledgement."""

    payload = json.dumps({"ack_for": ack_for, "status": status}, separators=(",", ":"))
    return _base_frame(
        message_id=ack_for + ":ack:" + sender,
        conversation_id=conversation_id,
        sender=sender,
        recipient=recipient,
        kind="ack",
        encoding="utf-8",
        sequence=sequence,
        chunk_index=0,
        chunk_count=1,
        metadata="",
        payload=payload,
    )


def validate_frame(frame: Mapping[str, Any]) -> None:
    required = {"protocol", "version", "message_id", "sender", "recipient", "kind", "payload", "crc32"}
    missing = sorted(required.difference(frame))
    if missing:
        raise EnvelopeError("missing fields: " + ", ".join(missing))
    if frame["protocol"] != PROTOCOL or frame["version"] != VERSION:
        raise EnvelopeError("unsupported protocol version")
    if frame["kind"] not in SUPPORTED_KINDS:
        raise EnvelopeError("unsupported kind: " + str(frame["kind"]))
    if not isinstance(frame["message_id"], str) or not frame["message_id"]:
        raise EnvelopeError("message_id must be non-empty")
    if frame["crc32"] != crc32(frame):
        raise EnvelopeError("CRC mismatch")
    if int(frame.get("chunk_index", 0)) < 0 or int(frame.get("chunk_count", 1)) < 1:
        raise EnvelopeError("invalid chunk coordinates")
    if int(frame.get("chunk_index", 0)) >= int(frame.get("chunk_count", 1)):
        raise EnvelopeError("chunk_index outside chunk_count")
    if int(frame.get("ttl", 1)) < 0:
        raise EnvelopeError("ttl must not be negative")
    if frame.get("kind") == "text" and frame.get("encoding") != "utf-8":
        raise EnvelopeError("text frames must use utf-8")


def encode_frame(frame: Mapping[str, Any]) -> bytes:
    validate_frame(frame)
    return json.dumps(frame, separators=(",", ":")).encode("utf-8")


def decode_frame(raw: bytes | str) -> OrderedDict:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    try:
        frame = json.loads(raw, object_pairs_hook=OrderedDict)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EnvelopeError("invalid JSON frame") from error
    if not isinstance(frame, Mapping):
        raise EnvelopeError("frame must be an object")
    validate_frame(frame)
    return OrderedDict(frame)


def resolve_recipient(handle: str, directory: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    """Resolve @username through a trusted local directory."""

    if not handle.startswith("@") or len(handle) == 1:
        raise EnvelopeError("recipient must be an @username")
    record = directory.get(handle.lower())
    if record is None or not record.get("account_id"):
        raise EnvelopeError("unknown recipient: " + handle)
    return record


@dataclass
class Deduplicator:
    limit: int = 256

    def __post_init__(self) -> None:
        self._seen: list[tuple[str, int]] = []

    def accept(self, frame: Mapping[str, Any]) -> bool:
        key = (str(frame["message_id"]), int(frame.get("chunk_index", 0)))
        if key in self._seen:
            return False
        self._seen.append(key)
        del self._seen[:-self.limit]
        return True


@dataclass
class ChunkAssembler:
    """Collect one logical message without delivering partial content."""

    def __post_init__(self) -> None:
        self._chunks: dict[tuple[str, int], dict[int, Mapping[str, Any]]] = {}

    def add(self, frame: Mapping[str, Any]) -> str | None:
        validate_frame(frame)
        key = (str(frame["message_id"]), int(frame.get("chunk_count", 1)))
        bucket = self._chunks.setdefault(key, {})
        bucket[int(frame.get("chunk_index", 0))] = frame
        count = key[1]
        if len(bucket) != count or set(bucket) != set(range(count)):
            return None
        ordered = [bucket[index] for index in range(count)]
        first = ordered[0]
        invariant_fields = ("conversation_id", "sender", "recipient", "kind", "encoding", "metadata")
        for frame_part in ordered[1:]:
            if any(frame_part.get(field, "") != first.get(field, "") for field in invariant_fields):
                raise EnvelopeError("chunk metadata does not agree")
        del self._chunks[key]
        return "".join(str(part.get("payload", "")) for part in ordered)
