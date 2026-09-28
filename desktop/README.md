# Desktop chat

This is a small laptop GUI for testing a USB-connected ESP-NOW node while the
Android app is being developed. It uses the same ASCII-safe base64 envelope as
the Android client, so emoji and other UTF-8 text do not depend on the laptop
terminal encoding.

From the repository root, with `pyserial` installed:

```text
python3 desktop/methodmeshenger_chat.py
```

Choose the ESP serial port, connect, and send messages. Incoming messages are
shown as chat text; delivery acknowledgements and node errors appear in the
status line. Outgoing messages show `✓` when the local node accepts the radio
send and `✓✓` when the peer node acknowledges receipt. These are delivery
receipts, not proof that a person has read the message.
