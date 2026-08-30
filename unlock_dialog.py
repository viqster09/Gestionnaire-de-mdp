"""Équivalent Python de ui/UnlockDialog.cpp."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from crypto_manager import DecryptionError
from vault import Vault


class UnlockDialog(QDialog):
    def __init__(self, vault_path: Path, parent=None):
        super().__init__(parent)
        self.vault_path = Path(vault_path)
        self.vault: Vault | None = None
        self._is_new = not self.vault_path.exists()

        self.setWindowTitle("PassVault — Déverrouillage" if not self._is_new else "PassVault — Nouveau coffre")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        info = QLabel(
            "Aucun coffre trouvé. Choisissez un mot de passe maître pour en créer un."
            if self._is_new
            else "Entrez votre mot de passe maître pour déverrouiller le coffre."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Mot de passe maître")
        self.password_edit.returnPressed.connect(self._on_submit)
        layout.addWidget(self.password_edit)

        if self._is_new:
            self.confirm_edit = QLineEdit()
            self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.confirm_edit.setPlaceholderText("Confirmer le mot de passe")
            self.confirm_edit.returnPressed.connect(self._on_submit)
            layout.addWidget(self.confirm_edit)
        else:
            self.confirm_edit = None

        submit_label = "Créer le coffre" if self._is_new else "Déverrouiller"
        self.submit_button = QPushButton(submit_label)
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)

        self.password_edit.setFocus()

    def _on_submit(self) -> None:
        password = self.password_edit.text()

        if not password:
            QMessageBox.warning(self, "PassVault", "Le mot de passe ne peut pas être vide.")
            return

        vault = Vault(self.vault_path)

        try:
            if self._is_new:
                if password != self.confirm_edit.text():
                    QMessageBox.warning(self, "PassVault", "Les mots de passe ne correspondent pas.")
                    return
                vault.create(password)
            else:
                vault.unlock(password)
        except DecryptionError:
            QMessageBox.critical(self, "PassVault", "Mot de passe incorrect.")
            return
        except Exception as exc:  # noqa: BLE001 — on affiche toute erreur crypto à l'utilisateur
            QMessageBox.critical(self, "PassVault", f"Erreur : {exc}")
            return

        self.vault = vault
        # Efface le champ de saisie best-effort (limite : voir secure_bytes.py)
        self.password_edit.clear()
        self.accept()
