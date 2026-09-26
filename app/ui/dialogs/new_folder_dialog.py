"""
Dialog for creating a new Google Drive folder directly from the Desktop App.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)


class NewFolderDialog(QDialog):
    """Modal dialog allowing user to create a new folder on Google Drive."""

    def __init__(self, parent_folder_name: str = "My Drive", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Folder on Google Drive")
        self.setMinimumWidth(420)
        self.setModal(True)

        self._parent_name = parent_folder_name
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title & Location Header
        title_label = QLabel("📁 Create New Folder")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title_label)

        location_label = QLabel(f"Location:  <b>{self._parent_name}</b>")
        location_label.setStyleSheet("color: #94a3b8; font-size: 13px;")
        layout.addWidget(location_label)

        # Folder Name Input
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        input_title = QLabel("Folder Name:")
        input_title.setStyleSheet("font-weight: 600; color: #f8fafc;")
        form_layout.addWidget(input_title)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Backups, Project Alpha, or Nested/Path/Folder")
        self.name_edit.setFocus()
        form_layout.addWidget(self.name_edit)

        layout.addLayout(form_layout)

        # Hint
        hint_label = QLabel("Tip: You can also use '/' to create nested subfolders at once.")
        hint_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(hint_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.create_btn = QPushButton("Create Folder")
        self.create_btn.setProperty("class", "primary-btn")
        self.create_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; padding: 8px 18px;")
        self.create_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.create_btn)

        layout.addLayout(btn_layout)

        # Enter key triggers create
        self.name_edit.returnPressed.connect(self._validate_and_accept)

    def _validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid folder name.")
            return
        self.accept()

    def get_folder_name(self) -> str:
        """Returns the entered folder name."""
        return self.name_edit.text().strip()
