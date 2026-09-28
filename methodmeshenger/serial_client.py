"""Run a two-peer MethodMeshenger client over one ESP serial link."""

from __future__ import annotations

import argparse
import threading

import serial

from .client import Client
from .directory import Directory, UserRecord


class SerialTransport:
    def __init__(self, port):
        self.port = port

    def send(self, raw: bytes) -> None:
        self.port.write(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat through a MethodMeshenger ESP-NOW node")
    parser.add_argument("port")
    parser.add_argument("--username", required=True, help="local handle, e.g. @alice")
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--peer", required=True, help="peer handle, e.g. @bob")
    parser.add_argument("--peer-device-id", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    directory = Directory()
    directory.add_user(UserRecord(args.username, args.device_id, (args.device_id,)))
    directory.add_user(UserRecord(args.peer, args.peer_device_id, (args.peer_device_id,)))

    with serial.Serial(args.port, args.baud, timeout=1) as port:
        transport = SerialTransport(port)
        client = Client(username=args.username, device_id=args.device_id, directory=directory, transport=transport)

        def reader() -> None:
            while True:
                line = port.readline()
                for frame in client.ingest_line(line):
                    print("< %s: %s" % (frame["sender"], frame["payload"]), flush=True)

        threading.Thread(target=reader, daemon=True).start()
        print("Connected. Type a message and press Enter; Ctrl-D exits.")
        for line in iter(input, ""):
            if line:
                client.send_text(args.peer, line)


if __name__ == "__main__":
    main()
