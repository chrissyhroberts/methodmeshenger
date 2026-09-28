# Secure session boundary

MethodMeshenger must not implement its own key agreement or ratchet. The
client needs an audited, maintained implementation of an asynchronous
authenticated session protocol; ESP nodes must see only opaque ciphertext.

## Required properties

- asynchronous setup while the recipient is offline;
- authenticated identity keys and explicit first-contact verification;
- forward secrecy and post-compromise recovery;
- skipped-message handling and replay protection;
- authenticated envelope metadata as associated data;
- durable, recoverable session state on the client only;
- no private keys or plaintext in ESP firmware, radio spools, or diagnostics.

The current repository exposes these requirements through
`methodmeshenger.session.SessionAdapter`. It deliberately contains no
cryptographic implementation. `associated_data()` gives the adapter a stable
binding for routing, chunk coordinates, expiry and content metadata.

The first concrete adapter is scaffolded in [`secure-session`](../secure-session/).
It uses vodozemac/Olm for asynchronous pre-key establishment and the Double
Ratchet, while keeping MethodMeshenger’s envelope binding outside the library.

## Decision

Use vodozemac/Olm for one-to-one sessions. vodozemac is Apache-2.0 licensed,
implements an asynchronous Olm Double Ratchet, and exposes encrypted state
pickling for client persistence.

The adapter is pinned to vodozemac `0.11`. Local tests now cover the first
pre-key exchange, ratcheted replies, envelope binding, encrypted account and
session pickles, and wrong-key rejection. The pickle helpers are deliberately
small: the host application must supply a platform-backed 32-byte key and
define its recovery policy. This proves the library boundary, not production
readiness; device verification, recovery UX, and Android FFI still need to be
implemented and tested.

Megolm is reserved for a later group-message design because its single-ratchet
trade-offs differ from one-to-one Olm.

## Implementation rule

Until the adapter has passed verification and interoperability
tests, the client remains explicitly marked development-only. It may exercise
transport, addressing, chunking and ACKs, but it must not be described as
secure messaging.
