# MethodMeshenger

An off-grid, ESP-NOW-first messenger companion for MethodMesh.

MethodMeshenger is being developed as a small communications system in its
own right: ESP nodes provide the radio path, a laptop or phone provides the
conversation interface, and MethodMesh/ODK can become a client later. The
project starts with two boards and two serial consoles so that radio delivery,
message identity and queue behaviour can be understood before BLE or Android
integration is added.

The wire format is designed from the outset for text, attachments and voice.
See [the protocol design](docs/PROTOCOL.md) before changing the firmware.

## Current status

The current test harness supports direct ESP-NOW messages between two ESP32-C3
nodes, with explicit peer/channel diagnostics, duplicate IDs and a stable
field-ordered checksum. It is not yet secure, store-and-forward, or a finished
messenger.

The working firmware is in [`firmware/methodmeshenger`](firmware/methodmeshenger).
