"""Équivalent Python de src/main.cpp."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from unlock_dialog import UnlockDialog

# Chemin du coffre : ~/.passvault/vault.dat (équivalent QStandardPaths)
VAULT_DIR = Path.home() / ".passvault"
VAULT_PATH = VAULT_DIR / "vault.dat"


def main() -> int:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setApplicationName("PassVault")

    dialog = UnlockDialog(VAULT_PATH)
    if dialog.exec() != UnlockDialog.DialogCode.Accepted or dialog.vault is None:
        return 0  # utilisateur a annulé

    window = MainWindow(dialog.vault)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
