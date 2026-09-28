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
The security boundary is described in [the security design](docs/SECURITY.md).

## Current status

The current test harness supports direct ESP-NOW messages between two ESP32-C3
nodes, with explicit peer/channel diagnostics, duplicate IDs, application ACKs
and a stable field-ordered checksum. The host-side reference library now also
defines signed onboarding records, `@username`/group resolution, a durable
spool, chunk assembly and a bootstrap encrypted-payload boundary. It is not
yet a finished secure messenger: the constrained firmware remains plaintext
and the final asynchronous ratchet is still ahead.

The working firmware is in [`firmware/methodmeshenger`](firmware/methodmeshenger).

## Laptop client

With `pyserial` installed, two laptops/terminals can use the client interface
instead of typing raw serial frames:

```text
python3 -m methodmeshenger.serial_client /dev/cu.usbmodemXXXX \
  --username @alice --device-id device-a \
  --peer @bob --peer-device-id device-b
```

Run the same command on the second node with the identities reversed. The
client resolves the handle, creates the canonical frame, tracks it in the
local spool, and marks it received when an application ACK comes back.

## Development tests

With the development dependency installed, run:

```text
python3 -m unittest discover -s tests -v
```

The Python client primitives are the reference for the constrained firmware;
the current ESP demo remains plaintext and development-only.
