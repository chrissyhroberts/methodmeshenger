import json
import unittest

from methodmeshenger.protocol import (
    Deduplicator,
    ChunkAssembler,
    EnvelopeError,
    ack_frame,
    chunk_text,
    chunk_content,
    decode_frame,
    encode_frame,
    resolve_recipient,
)


class ProtocolTests(unittest.TestCase):
    def test_crc_is_independent_of_json_key_order(self):
        frame = chunk_text(
            "hello",
            message_id="m1",
            conversation_id="c1",
            sender="alice",
            recipient="bob",
        )[0]
        raw = json.dumps(dict(reversed(list(frame.items())))).encode()
        self.assertEqual(decode_frame(raw)["message_id"], "m1")

    def test_tampering_is_rejected(self):
        frame = chunk_text("hello", message_id="m1", conversation_id="c1", sender="a", recipient="b")[0]
        frame["payload"] = "tampered"
        with self.assertRaises(EnvelopeError):
            encode_frame(frame)

    def test_text_chunks_reassemble_in_order(self):
        frames = chunk_text("abcdefghij", message_id="m1", conversation_id="c1", sender="a", recipient="b", max_chunk_chars=3)
        self.assertEqual([f["chunk_index"] for f in frames], [0, 1, 2, 3])
        self.assertEqual("".join(f["payload"] for f in frames), "abcdefghij")
        for frame in frames:
            decode_frame(encode_frame(frame))

    def test_ack_is_a_normal_valid_frame(self):
        frame = ack_frame(ack_for="m1", sender="bob", recipient="alice", status="received")
        self.assertEqual(decode_frame(encode_frame(frame))["kind"], "ack")

    def test_deduplicator_is_per_chunk(self):
        frames = chunk_text("abcd", message_id="m1", conversation_id="c1", sender="a", recipient="b", max_chunk_chars=2)
        dedupe = Deduplicator()
        self.assertTrue(dedupe.accept(frames[0]))
        self.assertFalse(dedupe.accept(frames[0]))
        self.assertTrue(dedupe.accept(frames[1]))

    def test_attachment_metadata_is_protected_and_reassembled(self):
        frames = chunk_content(
            "abcdef",
            kind="attachment",
            encoding="base64",
            metadata='{"name":"sample.bin","sha256":"abc"}',
            message_id="m2",
            conversation_id="c1",
            sender="a",
            recipient="b",
            max_chunk_chars=2,
        )
        assembler = ChunkAssembler()
        self.assertIsNone(assembler.add(frames[1]))
        self.assertEqual(assembler.add(frames[0]), None)
        self.assertEqual(assembler.add(frames[2]), "abcdef")
        frames[0]["metadata"] = '{"name":"tampered"}'
        with self.assertRaises(EnvelopeError):
            encode_frame(frames[0])

    def test_username_directory_resolution(self):
        directory = {"@alice": {"account_id": "acct-a", "device_id": "device-a"}}
        self.assertEqual(resolve_recipient("@alice", directory)["device_id"], "device-a")
        with self.assertRaises(EnvelopeError):
            resolve_recipient("@missing", directory)


if __name__ == "__main__":
    unittest.main()
