# MethodMeshenger test plan

## Automated protocol tests

Run from the repository root:

```text
python3 -m unittest discover -s tests -v
```

## Client smoke test

Install the development dependencies, then run one client per board using the
serial-client command in the root README. Send a short message in both
directions and confirm that each side prints the received text and that the
sender receives an `ack_received` event. Repeat the same message line to check
that the receiver does not duplicate it when the same frame is replayed.

These tests cover canonical CRC, tamper rejection, UTF-8 chunking, ACK frames,
per-chunk deduplication, username collision handling, group resolution and
durable spool state transitions.

## Hardware smoke test

1. Flash the same MicroPython image to two ESP32-C3 boards.
2. Copy `boot.py` and `main.py` from this repository to both boards.
3. Record each board's actual STA MAC and node ID from its `ready` event.
4. Confirm both boards report the same fixed channel.
5. Send a one-character text message in each direction.
6. Confirm the receiver reports `received_raw` and `message`.
7. Repeat the same frame and confirm it is deduplicated.
8. Disconnect the receiver, send again, and confirm the sender reports a
   delivery failure rather than a false application receipt.
9. Reconnect the receiver and verify the future spool layer retries the item.

The current firmware is still a transport demo. Do not use it to transmit
sensitive content until the encrypted client path is implemented.

The first physical end-to-end client run completed successfully on the two
ESP32-C3 boards: client A sent through `/dev/cu.usbmodem1101`, client B received
through `/dev/cu.usbmodem2101`, and the sender spool reached `received` after
the application acknowledgement returned. Both boards reported channel 6 and
`radio_ok: true` in both directions.

The next hardware checks are power-cycle recovery, delayed-ACK retry, and a
multi-chunk message while both serial clients remain active. The first
300-character, three-chunk transfer has now passed with exact reassembly and
all three sender spool items reaching `received`.
