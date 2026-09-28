# MethodMeshenger secure session

This crate is the client-side Apache-2.0 adapter around vodozemac/Olm. It is
not firmware and must never be linked into an ESP node. The transport carries
serialized ciphertext only.

The tests cover asynchronous pre-key establishment, ratcheted replies,
envelope-associated-data binding, and restoring account/session state from
encrypted vodozemac pickles. The host application still needs to provide the
actual platform-backed key storage and recovery UX before this can be enabled
in the messenger.
