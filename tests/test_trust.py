import unittest

from cryptography.hazmat.primitives.asymmetric import ed25519

from methodmeshenger.identity import make_record
from methodmeshenger.trust import TrustError, TrustStore


class TrustStoreTests(unittest.TestCase):
    def setUp(self):
        self.key = ed25519.Ed25519PrivateKey.generate()
        self.record = make_record(self.key, username="@alice", account_id="acct-a", device_id="device-a", encryption_public_key="enc-key")

    def test_observation_is_not_verification(self):
        store = TrustStore()
        self.assertEqual(store.observe(self.record).state, "unverified")
        with self.assertRaises(TrustError):
            store.require_verified("acct-a", "device-a")
        self.assertEqual(store.verify(self.record).state, "verified")
        self.assertEqual(store.require_verified("acct-a", "device-a").state, "verified")

    def test_key_change_requires_re_pairing(self):
        store = TrustStore()
        store.observe(self.record)
        replacement = make_record(ed25519.Ed25519PrivateKey.generate(), username="@alice", account_id="acct-a", device_id="device-a", encryption_public_key="enc-key")
        with self.assertRaises(TrustError):
            store.observe(replacement)

    def test_revocation_blocks_delivery_authorization(self):
        store = TrustStore()
        store.verify(self.record)
        store.revoke("acct-a", "device-a")
        with self.assertRaises(TrustError):
            store.require_verified("acct-a", "device-a")


if __name__ == "__main__":
    unittest.main()
