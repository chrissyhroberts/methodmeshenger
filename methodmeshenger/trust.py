"""Local, explicit trust decisions for signed user/device records."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping

from .identity import IdentityRecordError, verify_record


class TrustError(ValueError):
    """Raised when a trust decision would be unsafe or ambiguous."""


@dataclass(frozen=True)
class DeviceTrust:
    account_id: str
    device_id: str
    signing_key_fingerprint: str
    state: str = "unverified"


def signing_key_fingerprint(record: Mapping[str, str]) -> str:
    try:
        key = record["identity_signing_public_key"]
    except KeyError as error:
        raise IdentityRecordError("identity record has no signing key") from error
    return hashlib.sha256(key.encode("ascii")).hexdigest()


class TrustStore:
    """In-memory trust decisions; persistence belongs to the host platform."""

    def __init__(self) -> None:
        self._devices: dict[tuple[str, str], DeviceTrust] = {}

    def observe(self, record: Mapping[str, str]) -> DeviceTrust:
        verify_record(record)
        key = (record["account_id"], record["device_id"])
        fingerprint = signing_key_fingerprint(record)
        current = self._devices.get(key)
        if current and current.signing_key_fingerprint != fingerprint:
            raise TrustError("device identity key changed; require explicit re-pairing")
        if current:
            return current
        observed = DeviceTrust(*key, fingerprint)
        self._devices[key] = observed
        return observed

    def verify(self, record: Mapping[str, str]) -> DeviceTrust:
        observed = self.observe(record)
        verified = DeviceTrust(observed.account_id, observed.device_id, observed.signing_key_fingerprint, "verified")
        self._devices[(verified.account_id, verified.device_id)] = verified
        return verified

    def revoke(self, account_id: str, device_id: str) -> DeviceTrust:
        current = self._devices.get((account_id, device_id))
        if current is None:
            raise TrustError("cannot revoke an unknown device")
        revoked = DeviceTrust(current.account_id, current.device_id, current.signing_key_fingerprint, "revoked")
        self._devices[(account_id, device_id)] = revoked
        return revoked

    def require_verified(self, account_id: str, device_id: str) -> DeviceTrust:
        current = self._devices.get((account_id, device_id))
        if current is None or current.state != "verified":
            raise TrustError("device has not been explicitly verified")
        return current
