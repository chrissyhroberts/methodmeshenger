"""Explicit local address book for MethodMeshenger users and groups."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .protocol import EnvelopeError


@dataclass(frozen=True)
class UserRecord:
    username: str
    account_id: str
    devices: tuple[str, ...]
    public_keys: dict[str, str] = field(default_factory=dict)
    verified: bool = False


@dataclass(frozen=True)
class GroupRecord:
    group_id: str
    name: str
    members: tuple[str, ...]


class Directory:
    def __init__(self) -> None:
        self.users: dict[str, UserRecord] = {}
        self.groups: dict[str, GroupRecord] = {}

    @staticmethod
    def _handle(username: str) -> str:
        if not username.startswith("@") or len(username) < 2:
            raise EnvelopeError("usernames must look like @alice")
        return username.lower()

    def add_user(self, record: UserRecord) -> None:
        handle = self._handle(record.username)
        if not record.account_id or not record.devices:
            raise EnvelopeError("users need an account_id and at least one device")
        existing = self.users.get(handle)
        if existing and existing.account_id != record.account_id:
            raise EnvelopeError("username is already bound to another account")
        self.users[handle] = UserRecord(handle, record.account_id, tuple(record.devices), dict(record.public_keys), record.verified)

    def add_group(self, record: GroupRecord) -> None:
        if not record.group_id or not record.members:
            raise EnvelopeError("groups need an id and members")
        self.groups[record.group_id] = record

    def resolve(self, address: str) -> dict[str, Any]:
        if address.startswith("@"):
            record = self.users.get(self._handle(address))
            if record is None:
                raise EnvelopeError("unknown recipient: " + address)
            return {"type": "user", "account_id": record.account_id, "devices": list(record.devices), "verified": record.verified}
        record = self.groups.get(address)
        if record is None:
            raise EnvelopeError("unknown group: " + address)
        return {"type": "group", "group_id": record.group_id, "members": list(record.members)}

