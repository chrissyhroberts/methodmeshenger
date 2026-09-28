"""Signed account/device records used during local onboarding."""

from __future__ import annotations

import base64
import json
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519


class IdentityRecordError(ValueError):
    """Raised when an onboarding record is malformed or untrusted."""


def _canonical(record: Mapping[str, Any]) -> bytes:
    unsigned = {key: value for key, value in record.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_record(private_key: ed25519.Ed25519PrivateKey, *, username: str, account_id: str, device_id: str, encryption_public_key: str) -> dict[str, str]:
    record = {
        "username": username.lower(),
        "account_id": account_id,
        "device_id": device_id,
        "encryption_public_key": encryption_public_key,
    }
    record["identity_signing_public_key"] = base64.urlsafe_b64encode(
        private_key.public_key().public_bytes_raw()
    ).decode("ascii").rstrip("=")
    record["signature"] = base64.urlsafe_b64encode(private_key.sign(_canonical(record))).decode("ascii").rstrip("=")
    return record


def verify_record(record: Mapping[str, str]) -> bool:
    required = {"username", "account_id", "device_id", "encryption_public_key", "identity_signing_public_key", "signature"}
    if not required.issubset(record) or not str(record["username"]).startswith("@"):
        raise IdentityRecordError("incomplete identity record")
    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(_decode(record["identity_signing_public_key"]))
        public_key.verify(_decode(record["signature"]), _canonical(record))
    except (KeyError, ValueError, InvalidSignature) as error:
        raise IdentityRecordError("identity record signature is invalid") from error
    return True


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
