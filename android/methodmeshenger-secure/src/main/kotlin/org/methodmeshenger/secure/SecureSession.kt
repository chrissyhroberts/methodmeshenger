package org.methodmeshenger.secure

/**
 * Opaque encrypted payload returned by the audited Rust session adapter.
 * Associated data is supplied by the MethodMeshenger envelope and is never
 * silently discarded by the bridge.
 */
data class EncryptedPayload(
    val ciphertext: ByteArray,
    val associatedData: ByteArray,
) {
    override fun equals(other: Any?): Boolean =
        other is EncryptedPayload &&
            ciphertext.contentEquals(other.ciphertext) &&
            associatedData.contentEquals(other.associatedData)

    override fun hashCode(): Int = 31 * ciphertext.contentHashCode() + associatedData.contentHashCode()
}

/** Platform keystore boundary; implementations must not derive keys from usernames or device ids. */
interface SessionKeyStore {
    fun loadOrCreateKey(accountId: String): ByteArray
}

/**
 * Phone-facing contract for one-to-one secure sessions.
 *
 * Implementations are expected to be backed by the Rust/vodozemac adapter.
 * There is deliberately no `sendPlaintext` or fallback implementation here.
 */
interface SecureSessionBackend {
    fun createOutboundSession(recipientCurve25519Key: ByteArray, recipientOneTimeKey: ByteArray): Long

    fun acceptPreKeySession(senderCurve25519Key: ByteArray, preKeyMessage: ByteArray): InboundMessage

    fun encrypt(sessionHandle: Long, plaintext: ByteArray, associatedData: ByteArray): EncryptedPayload

    fun decrypt(sessionHandle: Long, ciphertext: ByteArray, associatedData: ByteArray): ByteArray

    fun pickleSession(sessionHandle: Long, key: ByteArray): String

    fun restoreSession(pickle: String, key: ByteArray): Long
}

data class InboundMessage(
    val sessionHandle: Long,
    val firstPlaintext: ByteArray,
)

/** Fails closed until the native Rust artifact is actually packaged by the host app. */
class NativeSecureSessionBackend : SecureSessionBackend {
    init {
        System.loadLibrary("methodmeshenger_secure_session")
    }

    override fun createOutboundSession(recipientCurve25519Key: ByteArray, recipientOneTimeKey: ByteArray): Long =
        nativeCreateOutboundSession(recipientCurve25519Key, recipientOneTimeKey)

    override fun acceptPreKeySession(senderCurve25519Key: ByteArray, preKeyMessage: ByteArray): InboundMessage =
        nativeAcceptPreKeySession(senderCurve25519Key, preKeyMessage)

    override fun encrypt(sessionHandle: Long, plaintext: ByteArray, associatedData: ByteArray): EncryptedPayload =
        nativeEncrypt(sessionHandle, plaintext, associatedData)

    override fun decrypt(sessionHandle: Long, ciphertext: ByteArray, associatedData: ByteArray): ByteArray =
        nativeDecrypt(sessionHandle, ciphertext, associatedData)

    override fun pickleSession(sessionHandle: Long, key: ByteArray): String =
        nativePickleSession(sessionHandle, key)

    override fun restoreSession(pickle: String, key: ByteArray): Long =
        nativeRestoreSession(pickle, key)

    private external fun nativeCreateOutboundSession(recipientCurve25519Key: ByteArray, recipientOneTimeKey: ByteArray): Long
    private external fun nativeAcceptPreKeySession(senderCurve25519Key: ByteArray, preKeyMessage: ByteArray): InboundMessage
    private external fun nativeEncrypt(sessionHandle: Long, plaintext: ByteArray, associatedData: ByteArray): EncryptedPayload
    private external fun nativeDecrypt(sessionHandle: Long, ciphertext: ByteArray, associatedData: ByteArray): ByteArray
    private external fun nativePickleSession(sessionHandle: Long, key: ByteArray): String
    private external fun nativeRestoreSession(pickle: String, key: ByteArray): Long
}
