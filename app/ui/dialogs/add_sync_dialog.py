"""
Dialog for configuring a new directory synchronization job.
"""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.database.models import SyncJobConfig


class AddSyncJobDialog(QDialog):
    """Dialog to create a new local-to-drive sync configuration."""

    def __init__(self, current_dest_id: str, current_dest_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Auto-Sync Job")
        self.setMinimumWidth(500)
        self.setModal(True)

        self.dest_id = current_dest_id
        self.dest_path = current_dest_path
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🔄 New Directory Synchronization Job")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        # Job Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Work Documents, Python Projects")
        form.addRow("Job Name:", self.name_edit)

        # Local Directory Picker
        dir_layout = QHBoxLayout()
        self.local_edit = QLineEdit()
        self.local_edit.setPlaceholderText("Select folder from your computer...")
        dir_layout.addWidget(self.local_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_local)
        dir_layout.addWidget(self.browse_btn)
        form.addRow("Local Folder:", dir_layout)

        # Google Drive Destination
        dest_info = QLabel(f"<b>{self.dest_path}</b> (ID: {self.dest_id})")
        dest_info.setStyleSheet("color: #38bdf8;")
        form.addRow("Drive Target:", dest_info)

        # Sync options
        self.chk_modified = QCheckBox("Monitor and sync file modifications (not only new files)")
        self.chk_modified.setChecked(True)
        form.addRow("", self.chk_modified)

        layout.addLayout(form)

        # Safety Notice
        safety_notice = QLabel("🛡️ Safe Sync: Local file deletions will NEVER automatically delete items on Google Drive.")
        safety_notice.setStyleSheet("color: #10b981; font-size: 11px;")
        layout.addWidget(safety_notice)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Create Sync Job")
        self.save_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

    def _browse_local(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Local Directory to Sync")
        if folder:
            self.local_edit.setText(folder)
            if not self.name_edit.text():
                self.name_edit.setText(Path(folder).name)

    def _validate_and_accept(self):
        name = self.name_edit.text().strip()
        local_dir = self.local_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Validation Error", "Please provide a name for this sync job.")
            return

        if not local_dir or not Path(local_dir).is_dir():
            QMessageBox.warning(self, "Validation Error", "Please select a valid local folder.")
            return

        self.accept()

    def get_sync_config(self) -> SyncJobConfig:
        return SyncJobConfig(
            name=self.name_edit.text().strip(),
            local_dir=self.local_edit.text().strip(),
            drive_folder_id=self.dest_id,
            drive_folder_path=self.dest_path,
            sync_modified=self.chk_modified.isChecked(),
            is_active=True
        )
