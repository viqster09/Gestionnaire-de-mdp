"""
Équivalent Python de CryptoManager.h/.cpp (passvault).

Utilise PyNaCl (bindings Python de libsodium — la MÊME bibliothèque C que
la version C++), via son module bas niveau `nacl.bindings`, qui expose les
fonctions libsodium quasi 1:1 avec la version C++ :
- Dérivation de clé : Argon2id (crypto_pwhash, ALG_ARGON2ID13)
- Chiffrement : XChaCha20-Poly1305 IETF (AEAD, nonce 24 octets)

Installation :
    pip install pynacl
"""

from __future__ import annotations

import nacl.bindings as sodium
import nacl.exceptions
import nacl.pwhash


class DecryptionError(Exception):
    """Levée en cas d'échec de déchiffrement (mauvais mot de passe ou
    fichier corrompu/altéré — le tag d'authentification ne correspond pas)."""

    def __init__(self) -> None:
        super().__init__(
            "Déchiffrement échoué : mot de passe incorrect ou fichier corrompu"
        )


class CryptoManager:
    """
    Encapsule toute la cryptographie du coffre.
    - Dérivation de clé : Argon2id via crypto_pwhash (résistant GPU/ASIC)
    - Chiffrement : XChaCha20-Poly1305 (AEAD, nonce 24 octets, sûr même
      généré aléatoirement sans risque pratique de collision)
    """

    SALT_BYTES = nacl.pwhash.argon2id.SALTBYTES  # 16
    KEY_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_KEYBYTES  # 32
    NONCE_BYTES = sodium.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES  # 24

    def __init__(self) -> None:
        # PyNaCl appelle sodium_init() automatiquement à l'import du module
        # `nacl._sodium` — pas d'équivalent explicite nécessaire ici,
        # contrairement à la version C++.
        pass

    def generate_salt(self) -> bytes:
        return sodium.randombytes(self.SALT_BYTES)

    def derive_key(self, password: bytes, salt: bytes) -> bytes:
        if len(salt) != self.SALT_BYTES:
            raise ValueError("Taille de sel invalide")

        # Argon2id : opslimit/memlimit "MODERATE" (~64 Mo RAM, ~0.7s CPU),
        # équivalent des constantes MODERATE côté C++. PyNaCl expose ces
        # constantes sous nacl.pwhash.argon2id (pas dans nacl.bindings).
        try:
            key = nacl.pwhash.argon2id.kdf(
                self.KEY_BYTES,
                password,
                salt,
                opslimit=nacl.pwhash.argon2id.OPSLIMIT_MODERATE,
                memlimit=nacl.pwhash.argon2id.MEMLIMIT_MODERATE,
            )
        except nacl.exceptions.CryptoError as exc:
            # Échec typiquement dû à un manque de mémoire disponible.
            raise RuntimeError(
                "Dérivation de clé échouée (mémoire insuffisante ?)"
            ) from exc

        return key

    def encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        if len(key) != self.KEY_BYTES:
            raise ValueError("Taille de clé invalide")

        nonce = sodium.randombytes(self.NONCE_BYTES)

        # Pas de données additionnelles authentifiées (AAD), comme en C++.
        ciphertext = sodium.crypto_aead_xchacha20poly1305_ietf_encrypt(
            plaintext, None, nonce, key
        )

        return nonce + ciphertext

    def decrypt(self, blob: bytes, key: bytes) -> bytes:
        if len(key) != self.KEY_BYTES:
            raise ValueError("Taille de clé invalide")

        min_len = self.NONCE_BYTES + sodium.crypto_aead_xchacha20poly1305_ietf_ABYTES
        if len(blob) < min_len:
            raise DecryptionError()

        nonce = blob[: self.NONCE_BYTES]
        ciphertext = blob[self.NONCE_BYTES :]

        try:
            plaintext = sodium.crypto_aead_xchacha20poly1305_ietf_decrypt(
                ciphertext, None, nonce, key
            )
        except nacl.exceptions.CryptoError:
            raise DecryptionError()

        return plaintext

    @staticmethod
    def secure_wipe(data: bytearray) -> None:
        """
        Efface un buffer de façon sécurisée.

        IMPORTANT : contrairement à QByteArray côté C++, un `bytes` Python
        est IMMUABLE — impossible à effacer en place. Cette fonction exige
        donc un `bytearray` mutable (ex: obtenu via SecureBytes.data()).
        Si tes secrets transitent par des `bytes` classiques, envisage
        SecureBytes (voir secure_bytes.py) qui les stocke en bytearray
        verrouillé en mémoire dès l'origine.
        """
        for i in range(len(data)):
            data[i] = 0