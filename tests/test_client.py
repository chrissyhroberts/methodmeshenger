import unittest

from methodmeshenger.client import Client
from methodmeshenger.directory import Directory, UserRecord
from methodmeshenger.spool import Spool


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, raw):
        self.sent.append(raw)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.directory = Directory()
        self.directory.add_user(UserRecord("@alice", "acct-a", ("device-a",)))
        self.directory.add_user(UserRecord("@bob", "acct-b", ("device-b",)))
        self.transport = FakeTransport()
        self.spool = Spool()
        self.alice = Client(username="@alice", device_id="device-a", directory=self.directory, spool=self.spool, transport=self.transport)
        self.bob = Client(username="@bob", device_id="device-b", directory=self.directory, transport=FakeTransport())

    def test_send_resolves_handle_and_tracks_ack(self):
        deliveries = self.alice.send_text("@bob", "hello", now_ms=100)
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(self.spool.pending(), [])
        self.assertEqual(self.spool.items[deliveries[0].key]["state"], "enroute")
        frame_line = self.transport.sent[0]
        self.bob.transport.sent = []
        self.bob.ingest_line('{"event":"message","frame":%s}' % frame_line.decode().strip())
        ack_line = self.bob.transport.sent[0]
        self.alice.ingest_line('{"event":"ack_received","frame":%s}' % ack_line.decode().strip())
        self.assertEqual(self.spool.items[deliveries[0].key]["state"], "received")

    def test_unknown_handle_is_rejected(self):
        with self.assertRaises(Exception):
            self.alice.send_text("@missing", "hello")


if __name__ == "__main__":
    unittest.main()
