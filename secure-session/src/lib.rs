//! Client-side Apache-2.0 MethodMeshenger adapter around vodozemac/Olm.
//! ESP nodes never link this crate; they carry serialized ciphertext only.

use serde::{Deserialize, Serialize};
use vodozemac::olm::{Account, AccountPickle, OlmMessage, Session, SessionConfig, SessionPickle};

#[derive(Debug, thiserror::Error)]
pub enum SessionError {
    #[error("session message encoding failed: {0}")]
    Encoding(#[from] serde_json::Error),
    #[error("vodozemac encryption failed: {0}")]
    Encryption(#[from] vodozemac::olm::EncryptionError),
    #[error("vodozemac decryption failed: {0}")]
    Decryption(#[from] vodozemac::olm::DecryptionError),
    #[error("vodozemac pickle failed: {0}")]
    Pickle(#[from] vodozemac::PickleError),
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

/// Encrypt an account pickle for durable local storage.
///
/// The key must be generated and protected by the host platform. It must not
/// be derived from a username, device id, or a repository constant.
pub fn pickle_account(account: &Account, key: &[u8; 32]) -> String {
    account.pickle().encrypt(key)
}

pub fn restore_account(ciphertext: &str, key: &[u8; 32]) -> Result<Account, SessionError> {
    let pickle = AccountPickle::from_encrypted(ciphertext, key)?;
    Ok(Account::from_pickle(pickle))
}

/// Encrypt a ratchet session pickle for durable local storage.
pub fn pickle_session(session: &Session, key: &[u8; 32]) -> String {
    session.pickle().encrypt(key)
}

pub fn restore_session(ciphertext: &str, key: &[u8; 32]) -> Result<Session, SessionError> {
    let pickle = SessionPickle::from_encrypted(ciphertext, key)?;
    Ok(Session::from_pickle(pickle))
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

    #[test]
    fn encrypted_pickles_preserve_account_and_ratchet_state() {
        let alice = Account::new();
        let mut bob = Account::new();
        bob.generate_one_time_keys(1);
        let bob_one_time_key = *bob.one_time_keys().values().next().expect("one-time key");
        let mut alice_session = create_outbound_session(&alice, bob.curve25519_key(), bob_one_time_key).expect("outbound session");
        let first = encrypt(&mut alice_session, b"before restart", b"frame-1").expect("first encrypt");
        let prekey: OlmMessage = serde_json::from_slice(&first).expect("pre-key message");
        let prekey = match prekey {
            OlmMessage::PreKey(message) => message,
            OlmMessage::Normal(_) => panic!("first message must establish a pre-key session"),
        };
        let inbound = bob.create_inbound_session(SessionConfig::version_1(), alice.curve25519_key(), &prekey).expect("inbound session");
        let bob_session = inbound.session;

        let key = [7u8; 32];
        let alice_account_pickle = pickle_account(&alice, &key);
        let bob_account_pickle = pickle_account(&bob, &key);
        let alice_session_pickle = pickle_session(&alice_session, &key);
        let bob_session_pickle = pickle_session(&bob_session, &key);
        let restored_alice = restore_account(&alice_account_pickle, &key).expect("restore Alice account");
        let restored_bob = restore_account(&bob_account_pickle, &key).expect("restore Bob account");
        assert_eq!(restored_alice.curve25519_key(), alice.curve25519_key());
        assert_eq!(restored_bob.curve25519_key(), bob.curve25519_key());
        let mut restored_alice_session = restore_session(&alice_session_pickle, &key).expect("restore Alice session");
        let mut restored_bob_session = restore_session(&bob_session_pickle, &key).expect("restore Bob session");

        let reply = encrypt(&mut restored_bob_session, b"after restart", b"frame-2").expect("reply encrypt");
        assert_eq!(decrypt(&mut restored_alice_session, &reply, b"frame-2").expect("reply decrypt"), b"after restart");
        assert!(matches!(restore_session(&alice_session_pickle, &[8u8; 32]), Err(SessionError::Pickle(_))));
    }
}
