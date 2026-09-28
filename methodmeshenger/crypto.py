"""Client-side bootstrap E2E encryption.

This is intentionally not the final asynchronous ratchet. It provides a
small, testable sealed-message boundary while the transport is being built:
X25519 derives a per-message key, ChaCha20-Poly1305 encrypts the payload, and
Ed25519 authenticates the sender. Do not treat this as a replacement for an
audited X3DH/Double-Ratchet implementation.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class CryptoError(ValueError):
    """Raised when an encrypted payload cannot be authenticated or opened."""


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _derive(shared: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"methodmeshenger/e2e/bootstrap/v1").derive(shared)


@dataclass
class Identity:
    signing: ed25519.Ed25519PrivateKey
    exchange: x25519.X25519PrivateKey

    @classmethod
    def generate(cls) -> "Identity":
        return cls(ed25519.Ed25519PrivateKey.generate(), x25519.X25519PrivateKey.generate())

    def public_record(self, account_id: str, device_id: str, username: str) -> dict[str, str]:
        return {
            "account_id": account_id,
            "device_id": device_id,
            "username": username,
            "identity_signing": _b64(self.signing.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
            "encryption": _b64(self.exchange.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)),
        }


def seal(plaintext: bytes, *, sender: Identity, recipient_exchange_public: bytes, associated_data: bytes) -> dict[str, str]:
    ephemeral = x25519.X25519PrivateKey.generate()
    shared = ephemeral.exchange(x25519.X25519PublicKey.from_public_bytes(recipient_exchange_public))
    nonce = os.urandom(12)
    ciphertext = ChaCha20Poly1305(_derive(shared)).encrypt(nonce, plaintext, associated_data)
    ephemeral_public = ephemeral.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    signature = sender.signing.sign(associated_data + ephemeral_public + nonce + ciphertext)
    return {"v": "1", "ephemeral": _b64(ephemeral_public), "nonce": _b64(nonce), "ciphertext": _b64(ciphertext), "signature": _b64(signature)}


def open_sealed(sealed: dict[str, str], *, recipient: Identity, sender_signing_public: bytes, associated_data: bytes) -> bytes:
    try:
        ephemeral_public = _unb64(sealed["ephemeral"])
        nonce = _unb64(sealed["nonce"])
        ciphertext = _unb64(sealed["ciphertext"])
        signature = _unb64(sealed["signature"])
        ed25519.Ed25519PublicKey.from_public_bytes(sender_signing_public).verify(signature, associated_data + ephemeral_public + nonce + ciphertext)
        shared = recipient.exchange.exchange(x25519.X25519PublicKey.from_public_bytes(ephemeral_public))
        return ChaCha20Poly1305(_derive(shared)).decrypt(nonce, ciphertext, associated_data)
    except (KeyError, ValueError, InvalidSignature) as error:
        raise CryptoError("sealed payload authentication failed") from error
