# MethodMeshenger roadmap

## Phase 1 — radio proof

- two-node direct ESP-NOW text delivery;
- stable envelope and integrity check;
- visible send, receive and failure diagnostics;
- laptop serial interface.

## Phase 2 — message lifecycle

- client-side bootstrap encryption boundary;
- signed user/device directory records;
- application acknowledgements;
- deduplication and ordering;
- bounded retry queue;
- reboot-safe spool;
- explicit expiry and failed-delivery states.

The reference implementation now covers the envelope, chunk assembly, signed
identity records, directory resolution and a durable host-side spool. The
remaining work in this phase is integration: a real client queue, retry policy
and secure session establishment.

The serial client and two-board end-to-end path are now working. Retry-after-
timeout and replay suppression are covered in the client and host tests; the
remaining hardware checks are power-cycle recovery and multi-chunk transfer.

Before secure messaging can be enabled, select and approve the audited client
session adapter described in [`SECURE_SESSION.md`](SECURE_SESSION.md).

## Phase 3 — content

- chunked attachments with metadata and hashes;
- recorded voice messages;
- live voice as a separately designed transport;
- human-readable history on the laptop.

## Phase 4 — device interface

- BLE gateway between phone and node;
- phone-side conversation UI;
- node discovery and pairing;
- MethodMesh capability/provider integration.

The project should not return to MethodMesh integration until Phase 1 and the
message lifecycle in Phase 2 are demonstrably reliable.
