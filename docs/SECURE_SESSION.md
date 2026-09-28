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

## Candidate decision

The natural protocol family is X3DH followed by Double Ratchet. The official
Signal specifications define the asynchronous setup and ratcheting properties.
The official `libsignal` repository exposes implementations used by Signal
clients, but it also states that external use is unsupported and is licensed
under AGPL-3.0. That creates a product/licensing decision before it can become
a MethodMeshenger dependency.

Noise is a useful framework for authenticated handshakes, but it is not by
itself a complete asynchronous messenger session or Double-Ratchet
implementation. Choosing Noise would require selecting and reviewing an
additional ratchet/session layer.

## Implementation rule

Until an approved adapter is selected, the client remains explicitly marked
development-only. It may exercise transport, addressing, chunking and ACKs,
but it must not be described as secure messaging.
