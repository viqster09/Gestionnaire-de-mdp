"""
Équivalent Python de SecureString.h (passvault).

Différences importantes avec la version C++ :
- Python ne garantit PAS l'absence de copies internes : les objets `bytes`
  sont immuables et l'interpréteur peut dupliquer des données en mémoire
  sans que tu le contrôles (int caching, optimisations, etc.).
  -> On utilise donc un `bytearray` (mutable) pour permettre l'effacement
     réel du contenu, et on limite au maximum les conversions vers `bytes`.
- Pas de copy-on-write façon QSharedDataPointer : ici, une copie de
  SecureBytes clone toujours explicitement le buffer (plus simple, plus
  sûr, moins optimisé — acceptable pour un coffre-fort de mots de passe).
- mlock (Linux/macOS) / VirtualLock (Windows) sont utilisés en best-effort
  via ctypes. Comme sodium_mlock, l'échec peut survenir si le processus
  n'a pas les droits nécessaires (ulimit -l trop bas sous Unix). On lève
  une exception plutôt que de continuer silencieusement sans protection.
- Le garbage collector Python n'est pas déterministe comme les destructeurs
  C++ : on complète __del__ par un `wipe()` explicite à appeler dès que
  possible (ex: juste après usage), ne pas compter uniquement sur le GC.
"""

from __future__ import annotations

import ctypes
import platform
import sys


class SecureMemoryError(RuntimeError):
    """Levée quand le verrouillage mémoire (mlock/VirtualLock) échoue."""


def _lock_memory(address: int, size: int) -> None:
    system = platform.system()
    if system == "Windows":
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        if not kernel32.VirtualLock(ctypes.c_void_p(address), ctypes.c_size_t(size)):
            raise SecureMemoryError(
                "VirtualLock a échoué : le processus n'a peut-être pas assez "
                "de quota de working set (voir SetProcessWorkingSetSize)."
            )
    else:
        libc_name = "libc.so.6" if system == "Linux" else None
        libc = ctypes.CDLL(libc_name, use_errno=True)
        if libc.mlock(ctypes.c_void_p(address), ctypes.c_size_t(size)) != 0:
            errno = ctypes.get_errno()
            raise SecureMemoryError(
                f"mlock a échoué (errno={errno}) : augmentez ulimit -l ou "
                "accordez la capability IPC_LOCK au processus."
            )


def _unlock_memory(address: int, size: int) -> None:
    system = platform.system()
    if system == "Windows":
        ctypes.windll.kernel32.VirtualUnlock(  # type: ignore[attr-defined]
            ctypes.c_void_p(address), ctypes.c_size_t(size)
        )
    else:
        libc_name = "libc.so.6" if system == "Linux" else None
        libc = ctypes.CDLL(libc_name, use_errno=True)
        libc.munlock(ctypes.c_void_p(address), ctypes.c_size_t(size))


def _memzero(address: int, size: int) -> None:
    """Écrase la zone mémoire avec des zéros (équivalent sodium_memzero)."""
    ctypes.memset(address, 0, size)


class SecureBytes:
    """
    Buffer d'octets sensible (mot de passe, clé) :
    - Verrouillé en mémoire (jamais swappé sur disque) pendant sa durée de vie.
    - Effacé de façon garantie (memset à zéro) au wipe() explicite et à la
      destruction de l'objet.
    - Volontairement NON copiable implicitement : `copy()` clone
      explicitement pour éviter des duplications silencieuses en mémoire
      non protégée.
    """

    __slots__ = ("_buf", "_view", "_addr", "_size", "_locked")

    def __init__(self, size: int = 0):
        self._size = size
        self._buf = bytearray(size)
        self._locked = False
        if size > 0:
            self._view = (ctypes.c_char * size).from_buffer(self._buf)
            self._addr = ctypes.addressof(self._view)
            _lock_memory(self._addr, size)
            self._locked = True
        else:
            self._view = None
            self._addr = 0

    @classmethod
    def from_bytes(cls, data: bytes | bytearray) -> "SecureBytes":
        s = cls(len(data))
        if len(data) > 0:
            s._buf[:] = data
        return s

    @classmethod
    def from_str(cls, text: str) -> "SecureBytes":
        # Point d'entrée UI (ex: champ de saisie -> SecureBytes) uniquement.
        # Le buffer intermédiaire encode() n'est pas protégé ; on l'efface
        # au mieux juste après usage (best-effort, comme pour QByteArray
        # dans la version C++ : Python peut avoir déjà interné/copié la str).
        utf8 = bytearray(text.encode("utf-8"))
        s = cls.from_bytes(utf8)
        for i in range(len(utf8)):
            utf8[i] = 0  # effacement best-effort de la copie intermédiaire
        return s

    def to_str(self) -> str:
        """Affichage UI ponctuel uniquement : la str résultante n'est pas protégée."""
        return bytes(self._buf).decode("utf-8")

    def to_bytes(self) -> bytes:
        """Copie non protégée — à n'utiliser que pour interfacer avec du code externe."""
        return bytes(self._buf)

    def data(self) -> bytearray:
        """Accès direct au buffer mutable protégé (lecture/écriture)."""
        return self._buf

    def size(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def copy(self) -> "SecureBytes":
        """Clone explicite dans une NOUVELLE zone verrouillée."""
        return SecureBytes.from_bytes(self._buf)

    def wipe(self) -> None:
        """Efface immédiatement le contenu (utilisable avant fin de portée)."""
        if self._size > 0 and self._addr:
            _memzero(self._addr, self._size)
            if self._locked:
                _unlock_memory(self._addr, self._size)
                self._locked = False
        self._buf = bytearray(0)
        self._view = None
        self._addr = 0
        self._size = 0

    def __del__(self):
        try:
            self.wipe()
        except Exception:
            # Ne jamais lever depuis __del__ (comportement indéfini en Python).
            pass

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        return f"SecureBytes(size={self._size})"  # jamais le contenu
