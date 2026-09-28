import unittest

from cryptography.hazmat.primitives.asymmetric import ed25519

from methodmeshenger.identity import IdentityRecordError, make_record, verify_record


class IdentityRecordTests(unittest.TestCase):
    def test_record_round_trip_and_tamper_detection(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        record = make_record(
            private_key,
            username="@Alice",
            account_id="acct-a",
            device_id="device-a",
            encryption_public_key="enc-key",
        )
        self.assertTrue(verify_record(record))
        record["username"] = "@mallory"
        with self.assertRaises(IdentityRecordError):
            verify_record(record)


if __name__ == "__main__":
    unittest.main()
