"""
Équivalent Python de core/Vault.cpp.

Format du fichier .vault sur disque :
    [ SALT_BYTES octets de sel, en clair ]
    [ blob chiffré = nonce || ciphertext || tag  (produit par CryptoManager.encrypt) ]

Le sel doit rester en clair : il est nécessaire pour re-dériver la clé à
chaque déverrouillage. Ce n'est pas un secret (c'est le rôle du sel).

La clé dérivée est mise en cache en mémoire (dans self._key) après un
déverrouillage réussi, pour éviter de relancer Argon2id (coûteux, ~0.7s)
à chaque sauvegarde pendant la session.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from crypto_manager import CryptoManager, DecryptionError


@dataclass
class Entry:
    name: str
    username: str = ""
    password: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "username": self.username,
            "password": self.password,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "Entry":
        return Entry(
            name=d.get("name", ""),
            username=d.get("username", ""),
            password=d.get("password", ""),
            notes=d.get("notes", ""),
        )


class Vault:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._crypto = CryptoManager()
        self._key: bytes | None = None
        self._salt: bytes | None = None
        self.entries: list[Entry] = []

    def exists(self) -> bool:
        return self.path.exists()

    # ---- Création d'un nouveau coffre --------------------------------

    def create(self, master_password: str) -> None:
        self._salt = self._crypto.generate_salt()
        self._key = self._crypto.derive_key(master_password.encode("utf-8"), self._salt)
        self.entries = []
        self.save()

    # ---- Déverrouillage d'un coffre existant --------------------------

    def unlock(self, master_password: str) -> None:
        raw = self.path.read_bytes()
        salt_len = CryptoManager.SALT_BYTES
        if len(raw) < salt_len:
            raise DecryptionError()

        self._salt = raw[:salt_len]
        blob = raw[salt_len:]

        key = self._crypto.derive_key(master_password.encode("utf-8"), self._salt)
        plaintext = self._crypto.decrypt(blob, key)  # lève DecryptionError si faux mdp

        self._key = key
        self.entries = [Entry.from_dict(d) for d in json.loads(plaintext.decode("utf-8"))]

    # ---- Sauvegarde -----------------------------------------------------

    def save(self) -> None:
        if self._key is None or self._salt is None:
            raise RuntimeError("Le coffre n'est pas déverrouillé")

        payload = json.dumps([e.to_dict() for e in self.entries]).encode("utf-8")
        blob = self._crypto.encrypt(payload, self._key)
        self.path.write_bytes(self._salt + blob)

    # ---- Verrouillage : efface la clé de la mémoire --------------------

    def lock(self) -> None:
        if self._key is not None:
            key_ba = bytearray(self._key)
            CryptoManager.secure_wipe(key_ba)
            self._key = None
        self.entries = []

    # ---- Opérations sur les entrées ------------------------------------

    def add_entry(self, entry: Entry) -> None:
        self.entries.append(entry)
        self.save()

    def update_entry(self, index: int, entry: Entry) -> None:
        self.entries[index] = entry
        self.save()

    def delete_entry(self, index: int) -> None:
        del self.entries[index]
        self.save()
