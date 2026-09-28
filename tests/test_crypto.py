import unittest

from methodmeshenger.crypto import CryptoError, Identity, open_sealed, seal


class CryptoTests(unittest.TestCase):
    def test_seal_and_open(self):
        alice = Identity.generate()
        bob = Identity.generate()
        aad = b"message-id|recipient|chunk-0"
        sealed = seal(b"private hello", sender=alice, recipient_exchange_public=bob.exchange.public_key().public_bytes_raw(), associated_data=aad)
        plaintext = open_sealed(sealed, recipient=bob, sender_signing_public=alice.signing.public_key().public_bytes_raw(), associated_data=aad)
        self.assertEqual(plaintext, b"private hello")

    def test_tampering_is_rejected(self):
        alice = Identity.generate()
        bob = Identity.generate()
        sealed = seal(b"private hello", sender=alice, recipient_exchange_public=bob.exchange.public_key().public_bytes_raw(), associated_data=b"aad")
        sealed["ciphertext"] = sealed["ciphertext"][:-1] + ("A" if sealed["ciphertext"][-1] != "A" else "B")
        with self.assertRaises(CryptoError):
            open_sealed(sealed, recipient=bob, sender_signing_public=alice.signing.public_key().public_bytes_raw(), associated_data=b"aad")

    def test_associated_data_is_authenticated(self):
        alice = Identity.generate()
        bob = Identity.generate()
        sealed = seal(b"private hello", sender=alice, recipient_exchange_public=bob.exchange.public_key().public_bytes_raw(), associated_data=b"original")
        with self.assertRaises(CryptoError):
            open_sealed(sealed, recipient=bob, sender_signing_public=alice.signing.public_key().public_bytes_raw(), associated_data=b"changed")


if __name__ == "__main__":
    unittest.main()
