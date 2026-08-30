"""Équivalent Python de ui/EntryDialog.cpp."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
)

from password_generator import generate_password
from vault import Entry


class EntryDialog(QDialog):
    def __init__(self, entry: Entry | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle entrée" if entry is None else "Modifier l'entrée")
        self.setMinimumWidth(420)

        form = QFormLayout(self)

        self.name_edit = QLineEdit(entry.name if entry else "")
        form.addRow("Nom :", self.name_edit)

        self.username_edit = QLineEdit(entry.username if entry else "")
        form.addRow("Identifiant :", self.username_edit)

        password_row = QHBoxLayout()
        self.password_edit = QLineEdit(entry.password if entry else "")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        password_row.addWidget(self.password_edit)

        self.toggle_button = QPushButton("👁")
        self.toggle_button.setFixedWidth(32)
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self._toggle_visibility)
        password_row.addWidget(self.toggle_button)

        self.generate_button = QPushButton("Générer")
        self.generate_button.clicked.connect(self._generate_password)
        password_row.addWidget(self.generate_button)

        form.addRow("Mot de passe :", password_row)

        self.length_spin = QSpinBox()
        self.length_spin.setRange(8, 128)
        self.length_spin.setValue(20)
        form.addRow("Longueur générée :", self.length_spin)

        self.notes_edit = QPlainTextEdit(entry.notes if entry else "")
        self.notes_edit.setFixedHeight(80)
        form.addRow("Notes :", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _toggle_visibility(self, checked: bool) -> None:
        self.password_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _generate_password(self) -> None:
        self.password_edit.setText(generate_password(length=self.length_spin.value()))
        self.toggle_button.setChecked(True)

    def result_entry(self) -> Entry:
        return Entry(
            name=self.name_edit.text().strip(),
            username=self.username_edit.text().strip(),
            password=self.password_edit.text(),
            notes=self.notes_edit.toPlainText(),
        )
