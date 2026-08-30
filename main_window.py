"""Équivalent Python de ui/MainWindow.cpp."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from entry_dialog import EntryDialog
from vault import Vault

COL_NAME, COL_USERNAME, COL_PASSWORD, COL_NOTES = range(4)


class MainWindow(QMainWindow):
    def __init__(self, vault: Vault):
        super().__init__()
        self.vault = vault
        self.setWindowTitle(f"PassVault — {vault.path.name}")
        self.resize(720, 480)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nom", "Identifiant", "Mot de passe", "Notes"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Ajouter")
        add_btn.clicked.connect(self._add_entry)
        buttons.addWidget(add_btn)

        edit_btn = QPushButton("Modifier")
        edit_btn.clicked.connect(self._edit_selected)
        buttons.addWidget(edit_btn)

        delete_btn = QPushButton("Supprimer")
        delete_btn.clicked.connect(self._delete_selected)
        buttons.addWidget(delete_btn)

        copy_btn = QPushButton("Copier le mot de passe")
        copy_btn.clicked.connect(self._copy_password)
        buttons.addWidget(copy_btn)

        lock_btn = QPushButton("Verrouiller")
        lock_btn.clicked.connect(self._lock)
        buttons.addWidget(lock_btn)

        layout.addLayout(buttons)

        self._refresh_table()

    # ---- Rendu de la table ----------------------------------------------

    def _refresh_table(self) -> None:
        self.table.setRowCount(len(self.vault.entries))
        for row, entry in enumerate(self.vault.entries):
            self.table.setItem(row, COL_NAME, QTableWidgetItem(entry.name))
            self.table.setItem(row, COL_USERNAME, QTableWidgetItem(entry.username))
            masked = QTableWidgetItem("•" * min(len(entry.password), 12) or "—")
            masked.setData(Qt.ItemDataRole.UserRole, entry.password)
            self.table.setItem(row, COL_PASSWORD, masked)
            self.table.setItem(row, COL_NOTES, QTableWidgetItem(entry.notes))

    def _selected_row(self) -> int | None:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    # ---- Actions ----------------------------------------------------------

    def _add_entry(self) -> None:
        dialog = EntryDialog(parent=self)
        if dialog.exec() == EntryDialog.DialogCode.Accepted:
            entry = dialog.result_entry()
            if not entry.name:
                QMessageBox.warning(self, "PassVault", "Le nom ne peut pas être vide.")
                return
            self.vault.add_entry(entry)
            self._refresh_table()

    def _edit_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        dialog = EntryDialog(entry=self.vault.entries[row], parent=self)
        if dialog.exec() == EntryDialog.DialogCode.Accepted:
            self.vault.update_entry(row, dialog.result_entry())
            self._refresh_table()

    def _delete_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        entry = self.vault.entries[row]
        confirm = QMessageBox.question(
            self, "PassVault", f"Supprimer l'entrée « {entry.name} » ?"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.vault.delete_entry(row)
            self._refresh_table()

    def _copy_password(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        password = self.vault.entries[row].password
        QApplication.clipboard().setText(password)
        QMessageBox.information(
            self, "PassVault", "Mot de passe copié (pensez à vider le presse-papiers après usage)."
        )

    def _lock(self) -> None:
        self.vault.lock()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802 — override Qt
        self.vault.lock()
        super().closeEvent(event)
