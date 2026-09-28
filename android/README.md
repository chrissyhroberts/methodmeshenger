# Android integration boundary

This directory contains the standalone MethodMeshenger Android app and its
phone-side boundary for the secure session adapter. It is intentionally a
small Kotlin layer rather than a second cryptographic implementation.

The eventual Android build will package a native library built from
`../secure-session`. The Kotlin layer must never implement a plaintext
fallback: if the native adapter is absent, unsupported, or cannot restore its
protected state, the operation fails visibly.

The app is currently a shell: node discovery, the Rust native packaging, and
the platform keystore policy are the next integration steps. MethodMesh is not
part of this build.
