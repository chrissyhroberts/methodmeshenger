# MethodMeshenger

The small, serial-first ESP-NOW messenger testbed.

This is intentionally separate from the Android MethodMesh transport. The
first milestone is boring on purpose: flash two ESP32 boards, connect each to
a laptop, and exchange messages over ESP-NOW. BLE, Android and MethodMesh
integration come later.

## First test

1. Flash a MicroPython image suitable for the board.
2. Copy `boot.py`, `wire.py` and `main.py` to each board.
3. Open one serial console per board at 115200 baud.
4. Send a line of text in either console.

The node prints JSON events for received messages and accepts plain text for
outgoing direct messages between the two current test boards. The radio
diagnostics include the actual MAC addresses, channel and delivery result.

The current test envelope has a version, message ID, conversation, sender,
recipient, sequence/chunk fields, type, payload and stable field-ordered CRC.
Valid messages produce application ACKs and duplicate messages are ignored
locally. The forward-looking envelope for attachments and voice is documented
in [`docs/PROTOCOL.md`](../../docs/PROTOCOL.md). This is a transport testbed,
not yet a secure or production messenger.

## Laptop tooling

The optional `serial_chat.py` helper provides the same interface from a laptop
when `pyserial` is installed:

```text
python3 serial_chat.py /dev/cu.usbmodemXXXX
```

Use two terminals and two boards. On Windows, pass the relevant `COM` port.
