# MethodMeshenger security design

## Security boundary

MethodMeshenger must provide end-to-end encryption from the user-facing client
to the destination user-facing client. ESP nodes are transport infrastructure:
they may route, retry and spool opaque ciphertext, but must not need plaintext
keys or plaintext message content.

This means:

```text
Laptop/phone A --encrypted content--> ESP node A
                                      ESP-NOW relay/spool
Laptop/phone B <--encrypted content-- ESP node B
```

BLE encryption, ESP-NOW peer encryption and filesystem protection are useful
defence in depth, but none of them replaces end-to-end encryption.

The current MicroPython text firmware is a lab transport and is not secure. It
must not be used for sensitive data until encrypted client payloads are in use.

## Identity and addressing

MAC addresses are radio addresses, not user identities. A user identity should
be represented by a long-term signing public key, with a stable fingerprint
used as the immutable account identity.

Each installation may have one or more devices. A device has its own device
key and node ID, but the user-facing address is a signed username binding:

```json
{
  "username": "@alice",
  "account_id": "acct-key-fingerprint",
  "device_id": "device-key-fingerprint",
  "public_keys": {
    "identity_signing": "...",
    "encryption": "..."
  },
  "signature": "..."
}
```

The spool is keyed by the resolved stable account/device identity, never by a
mutable username. `@alice` is a directory lookup and presentation handle;
`account_id` and `device_id` are what make routing and key selection safe.

Username claims must be verified or manually trusted. A node must not accept a
new public key merely because somebody announces the same username.

Signature validity and operator trust are separate: a newly observed device
starts unverified, and a changed signing key requires explicit re-pairing. A
local trust decision can be revoked; discovery alone is never permission to
deliver protected content.

## One-to-one messages

The long-term target is an asynchronous authenticated key agreement followed
by a ratcheting session:

1. users exchange or verify identity public keys;
2. the recipient publishes a signed prekey bundle for offline initiation;
3. the sender establishes a shared secret using an X3DH-style exchange;
4. both clients use a Double Ratchet to derive a fresh message key for each
   message;
5. each message payload is encrypted with an AEAD construction and the
   envelope is authenticated as associated data.

X3DH is designed for asynchronous messaging where the recipient may be
offline, and Double Ratchet derives new keys as messages and DH ratchets
advance. These are established protocol designs, not a suggestion to invent a
MethodMeshenger-specific handshake. See the [X3DH specification](https://signal.org/docs/specifications/x3dh/)
and [Double Ratchet specification](https://signal.org/docs/specifications/doubleratchet/).

## Group messages

The first secure group implementation should use per-recipient encrypted
copies of the message key. This is less efficient but easy to reason about and
does not require a long-lived shared group secret on every node.

Later, a proper group protocol such as MLS or an audited sender-key design can
be considered. A group ID is an address, not a secret. Membership changes must
rotate whatever group encryption state is eventually adopted.

## Payload encryption

The repository now includes a small Python bootstrap implementation in
`methodmeshenger/crypto.py`. It is useful for testing the encrypted payload
boundary and associated-data handling, but it is explicitly not the final
offline messaging protocol: it does not implement prekey bundles, skipped-key
management, ratchet state or recovery. The ESP firmware must not be described
as E2E-secure until the client path uses a complete, reviewed asynchronous
protocol.

The encrypted content should eventually contain:

```json
{
  "cipher": "audited-aead",
  "nonce": "...",
  "ciphertext": "..."
}
```

The following envelope fields should be authenticated as associated data:

```text
protocol, version, message_id, conversation_id, sender, recipient,
kind, encoding, sequence, chunk_index, chunk_count, created_at_ms,
expires_at_ms, ttl
```

This prevents an intermediary from changing routing or chunk metadata without
causing decryption failure. The payload itself should use an audited AEAD
implementation such as XChaCha20-Poly1305; libsodium documents both the
X25519 key-exchange family and the recommended AEAD APIs. See
[libsodium key exchange](https://doc.libsodium.org/key_exchange) and
[libsodium encrypted messages](https://doc.libsodium.org/secret-key_cryptography/encrypted-messages).

## What the ESP node may still reveal

End-to-end encryption protects content, but a radio relay may still see or
infer:

- sender and next-hop radio addresses;
- message size and chunk count;
- timing and retry behaviour;
- delivery status;
- possibly a recipient routing token.

Metadata minimisation, padding and opaque routing tokens can be added later.
They should not be confused with content confidentiality.

## Implementation rules

1. Do not write a new cryptographic primitive or handshake.
2. Do not use a MAC address as a user identity or encryption key.
3. Never reuse an AEAD nonce with the same key.
4. Never put plaintext in the ESP spool or diagnostic log.
5. Keep private keys out of firmware images and repository fixtures.
6. Treat key verification and recovery as part of the product, not an
   afterthought.
7. Keep the unencrypted serial demo clearly marked as development-only.

## Security milestones

1. Define and test the signed identity/username record.
2. Add an encrypted client-side text message using a vetted library.
3. Make ESP nodes carry opaque ciphertext without parsing it.
4. Add offline recipient prekeys and authenticated session setup.
5. Add ratcheting one-to-one messages.
6. Add encrypted chunked attachments and voice.
7. Add groups and membership rotation.
