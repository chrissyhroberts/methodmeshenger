# MethodMeshenger secure session

This crate is the client-side Apache-2.0 adapter around vodozemac/Olm. It is
not firmware and must never be linked into an ESP node. The transport carries
serialized ciphertext only.

The first test covers asynchronous pre-key establishment, ratcheted reply,
and envelope-associated-data binding. Account and session pickles still need a
client storage layer with a separately managed encryption key before this can
be enabled in the messenger.
