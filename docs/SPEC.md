# MethodMeshenger system specification (draft)

## Purpose

MethodMeshenger is an off-grid messaging sidecar for MethodMesh. It provides a
user-facing messaging model over ESP-NOW while keeping transport, identity,
security and content lifecycle separable.

## System roles

### Client

A laptop or phone client owns user identity, username resolution, encryption
keys, conversations and presentation. It can connect to a nearby ESP node over
serial, BLE or another local link.

### Node

An ESP node owns radio transport, peer discovery, bounded queues, forwarding,
delivery retries and hardware diagnostics. It must treat application payloads
as opaque ciphertext once secure messaging is enabled.

### Directory

The directory maps human handles such as `@alice` to trusted account and
device public keys. In the first offline implementation this is local and
explicitly trusted; later it may be exchanged between clients or transported
in signed records.

## Addressing

- `device_id` is a stable public-key fingerprint for a physical endpoint.
- `account_id` identifies the user identity controlling one or more devices.
- `@username` is a mutable presentation handle resolved through a trusted
  directory.
- `group_id` identifies a group, whose membership and cryptographic state are
  separate from its display name.
- radio MAC addresses are never user identities.

An outgoing message is resolved once at the client. The spool keys its route by
stable device/account identity, not by username.

## Onboarding a new node

1. The node generates a device keypair and node ID on first boot.
2. It exposes a short-lived onboarding service over USB or BLE.
3. The client reads the node fingerprint and asks the operator to verify it.
4. The operator assigns a username/device role and trusted peers/groups.
5. The client sends signed transport configuration and closes onboarding mode.
6. The node may then advertise signed discovery beacons over ESP-NOW.

The first implementation is USB-first: a human physically selects the serial
port, reads the fingerprint, and confirms it. BLE discovery can be added later,
but it must not silently turn radio visibility into trust. The reference
library contains the signed identity-record shape used by this ceremony.

Discovery is not trust. A beacon can make a node visible; only an authenticated
identity record makes it an acceptable recipient or relay.

## Message lifecycle

```text
compose -> resolve @handle -> encrypt -> enqueue -> radio send
       -> radio result -> application receipt -> assembled -> displayed
```

The radio result is not an application receipt. The sender must track at least
`queued`, `enroute`, `received`, `assembled`, `expired` and `failed`.

## Content

Text, attachments and voice share the v1 envelope. Large or binary content is
chunked using one `message_id` and explicit chunk coordinates. A receiver only
delivers a non-text item after all authenticated chunks and its content hash
are present.

## Security

See [`SECURITY.md`](SECURITY.md). The short version is: encryption belongs at
the client boundary, ESP nodes spool ciphertext, and no new cryptographic
handshake is invented for this project.

## Current implementation boundary

The repository currently contains a serial-first MicroPython transport testbed
and a Python reference library for envelopes, directory resolution, spooling,
signed onboarding records and a bootstrap encrypted-payload boundary. The
MicroPython demo is intentionally not an E2E-secure messenger yet. A complete
X3DH/Double-Ratchet client remains a deliberate security milestone, not a
firmware shortcut.
