"""Portable MethodMeshenger protocol primitives."""

from .protocol import (
    Deduplicator,
    EnvelopeError,
    ack_frame,
    chunk_text,
    decode_frame,
    encode_frame,
    resolve_recipient,
)

__all__ = [
    "Deduplicator",
    "EnvelopeError",
    "ack_frame",
    "chunk_text",
    "decode_frame",
    "encode_frame",
    "resolve_recipient",
]
