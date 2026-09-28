import unittest

from methodmeshenger.protocol import chunk_text
from methodmeshenger.session import SessionError, associated_data, require_secure_adapter


class SessionBoundaryTests(unittest.TestCase):
    def test_associated_data_binds_envelope_fields(self):
        frame = chunk_text("hello", message_id="m1", conversation_id="c1", sender="a", recipient="b")[0]
        original = associated_data(frame)
        frame["recipient"] = "c"
        self.assertNotEqual(original, associated_data(frame))

    def test_protected_delivery_cannot_silently_fall_back_to_plaintext(self):
        with self.assertRaises(SessionError):
            require_secure_adapter(None)


if __name__ == "__main__":
    unittest.main()
