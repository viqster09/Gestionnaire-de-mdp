"""Équivalent Python de core/PasswordGenerator.cpp."""

from __future__ import annotations

import secrets
import string


def generate_password(
    length: int = 20,
    use_lower: bool = True,
    use_upper: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """
    Génère un mot de passe aléatoire cryptographiquement sûr.

    Utilise `secrets` (basé sur os.urandom / CSPRNG du système), et non
    `random` qui n'est PAS cryptographiquement sûr.
    """
    alphabet = ""
    if use_lower:
        alphabet += string.ascii_lowercase
    if use_upper:
        alphabet += string.ascii_uppercase
    if use_digits:
        alphabet += string.digits
    if use_symbols:
        alphabet += "!@#$%^&*()-_=+[]{};:,.<>?"

    if not alphabet:
        raise ValueError("Au moins une catégorie de caractères doit être activée")

    return "".join(secrets.choice(alphabet) for _ in range(length))
