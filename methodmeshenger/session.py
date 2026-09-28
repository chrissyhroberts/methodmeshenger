"""Application boundary for an audited end-to-end session implementation.

This module intentionally contains no cryptography. A production adapter must
delegate to a maintained implementation of an asynchronous authenticated
session protocol; MethodMeshenger owns only envelope binding and lifecycle.
"""

from __future__ import annotations

from typing import Protocol

from .protocol import EnvelopeError


class SessionError(ValueError):
    """Raised when a secure session cannot protect or open a message."""


class SessionAdapter(Protocol):
    def encrypt(self, plaintext: bytes, *, associated_data: bytes, recipient: str) -> bytes: ...

    def decrypt(self, ciphertext: bytes, *, associated_data: bytes, sender: str) -> bytes: ...


def associated_data(frame: dict) -> bytes:
    """Bind routing and chunk metadata to the external session ciphertext."""

    fields = (
        "protocol", "version", "message_id", "conversation_id", "sender",
        "recipient", "kind", "encoding", "sequence", "chunk_index",
        "chunk_count", "created_at_ms", "expires_at_ms", "ttl", "metadata",
    )
    missing = [field for field in fields if field not in frame]
    if missing:
        raise EnvelopeError("cannot bind incomplete frame: " + ", ".join(missing))
    return b"|".join(str(frame[field]).encode("utf-8") for field in fields)


def require_secure_adapter(adapter: SessionAdapter | None) -> SessionAdapter:
    if adapter is None:
        raise SessionError("secure session adapter is required for protected delivery")
    return adapter
