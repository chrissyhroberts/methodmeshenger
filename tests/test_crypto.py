import unittest
import base64

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
        ciphertext = bytearray(base64.urlsafe_b64decode(sealed["ciphertext"] + "=" * (-len(sealed["ciphertext"]) % 4)))
        ciphertext[0] ^= 1
        sealed["ciphertext"] = base64.urlsafe_b64encode(bytes(ciphertext)).decode("ascii").rstrip("=")
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
