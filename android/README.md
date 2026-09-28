# Android integration boundary

This directory defines the phone-side boundary for the secure session adapter.
It is intentionally a small Kotlin library contract rather than a second
cryptographic implementation.

The eventual Android build will package a native library built from
`../secure-session`. The Kotlin layer must never implement a plaintext
fallback: if the native adapter is absent, unsupported, or cannot restore its
protected state, the operation fails visibly.

The native packaging step is not enabled yet because this repository does not
currently contain the MethodMesh Android host project, its NDK configuration,
or the platform keystore policy. Those choices belong to the host app. The
Kotlin API below is the stable seam the host can depend on while that work is
added.
