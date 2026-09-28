import tempfile
import unittest
from pathlib import Path

from methodmeshenger.directory import Directory, GroupRecord, UserRecord
from methodmeshenger.protocol import EnvelopeError, chunk_text, crc32
from methodmeshenger.spool import Spool


class DirectoryAndSpoolTests(unittest.TestCase):
    def frame(self):
        return chunk_text("hello", message_id="m1", conversation_id="c1", sender="a", recipient="device-b")[0]

    def test_username_collision_is_rejected(self):
        directory = Directory()
        directory.add_user(UserRecord("@alice", "acct-a", ("device-a",)))
        with self.assertRaises(EnvelopeError):
            directory.add_user(UserRecord("@alice", "acct-other", ("device-x",)))

    def test_group_resolves_to_members(self):
        directory = Directory()
        directory.add_group(GroupRecord("field-team", "@field-team", ("device-a", "device-b")))
        self.assertEqual(directory.resolve("field-team")["members"], ["device-a", "device-b"])

    def test_spool_survives_reload_and_tracks_states(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spool.json"
            spool = Spool(path)
            key = spool.enqueue(self.frame(), now_ms=1)
            spool.transition(key, "enroute", now_ms=2)
            spool.transition(key, "failed", error="radio timeout", now_ms=3)
            reloaded = Spool(path)
            self.assertEqual(reloaded.pending("device-b")[0]["attempts"], 1)
            self.assertEqual(reloaded.pending()[0]["error"], "radio timeout")

    def test_terminal_item_is_not_replaced(self):
        spool = Spool()
        frame = self.frame()
        key = spool.enqueue(frame)
        spool.transition(key, "enroute")
        spool.transition(key, "received")
        spool.transition(key, "assembled")
        changed = chunk_text("changed", message_id="m1", conversation_id="c1", sender="a", recipient="device-b")[0]
        spool.enqueue(changed)
        self.assertEqual(spool.items[key]["frame"]["payload"], "hello")

    def test_spool_rejects_invalid_transition_and_expires(self):
        spool = Spool()
        frame = self.frame()
        frame["expires_at_ms"] = 10
        frame["crc32"] = crc32(frame)
        key = spool.enqueue(frame, now_ms=1)
        with self.assertRaises(EnvelopeError):
            spool.transition(key, "assembled")
        self.assertEqual(spool.expire_due(10), [key])


if __name__ == "__main__":
    unittest.main()
