//! Client-side Apache-2.0 MethodMeshenger adapter around vodozemac/Olm.
//! ESP nodes never link this crate; they carry serialized ciphertext only.

use serde::{Deserialize, Serialize};
use vodozemac::olm::{Account, OlmMessage, Session, SessionConfig};

#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("session message encoding failed: {0}")]
    Encoding(#[from] serde_json::Error),
    #[error("vodozemac encryption failed: {0}")]
    Encryption(#[from] vodozemac::olm::EncryptionError),
    #[error("vodozemac decryption failed: {0}")]
    Decryption(#[from] vodozemac::olm::DecryptionError),
    #[error("associated data did not match the session envelope")]
    AssociatedDataMismatch,
}

#[derive(Debug, Serialize, Deserialize)]
struct ProtectedPayload<'a> {
    associated_data: &'a [u8],
    plaintext: &'a [u8],
}

#[derive(Debug, Serialize, Deserialize)]
struct OpenedPayload {
    associated_data: Vec<u8>,
    plaintext: Vec<u8>,
}

pub fn encrypt(session: &mut Session, plaintext: &[u8], associated_data: &[u8]) -> Result<Vec<u8>, SessionError> {
    let protected = serde_json::to_vec(&ProtectedPayload { associated_data, plaintext })?;
    let message = session.encrypt(protected)?;
    Ok(serde_json::to_vec(&message)?)
}

pub fn decrypt(session: &mut Session, ciphertext: &[u8], associated_data: &[u8]) -> Result<Vec<u8>, SessionError> {
    let message: OlmMessage = serde_json::from_slice(ciphertext)?;
    let opened: OpenedPayload = serde_json::from_slice(&session.decrypt(&message)?)?;
    if opened.associated_data != associated_data {
        return Err(SessionError::AssociatedDataMismatch);
    }
    Ok(opened.plaintext)
}

pub fn create_outbound_session(account: &Account, recipient_curve25519: vodozemac::Curve25519PublicKey, recipient_one_time_key: vodozemac::Curve25519PublicKey) -> Result<Session, vodozemac::olm::SessionCreationError> {
    account.create_outbound_session(SessionConfig::version_1(), recipient_curve25519, recipient_one_time_key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn asynchronous_prekey_and_ratchet_round_trip() {
        let alice = Account::new();
        let mut bob = Account::new();
        bob.generate_one_time_keys(1);
        let bob_one_time_key = *bob.one_time_keys().values().next().expect("one-time key");
        let mut alice_session = create_outbound_session(&alice, bob.curve25519_key(), bob_one_time_key).expect("outbound session");
        let first = encrypt(&mut alice_session, b"hello", b"frame-a").expect("encrypt");
        let prekey: OlmMessage = serde_json::from_slice(&first).expect("pre-key message");
        let prekey = match prekey {
            OlmMessage::PreKey(message) => message,
            OlmMessage::Normal(_) => panic!("first message must establish a pre-key session"),
        };
        let inbound = bob.create_inbound_session(SessionConfig::version_1(), alice.curve25519_key(), &prekey).expect("inbound session");
        let mut bob_session = inbound.session;
        assert_eq!(inbound.plaintext, serde_json::to_vec(&ProtectedPayload { associated_data: b"frame-a", plaintext: b"hello" }).expect("expected payload"));
        let reply = encrypt(&mut bob_session, b"world", b"frame-b").expect("reply encrypt");
        assert_eq!(decrypt(&mut alice_session, &reply, b"frame-b").expect("reply decrypt"), b"world");
        assert!(matches!(decrypt(&mut alice_session, &reply, b"wrong"), Err(SessionError::Decryption(_)) | Err(SessionError::AssociatedDataMismatch)));
    }
}
