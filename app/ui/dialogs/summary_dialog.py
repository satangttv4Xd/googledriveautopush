"""
Pre-Push Summary Dialog.
Displays file count, total size, target Google Drive destination, conflict policy,
and allows user to confirm or cancel before initiating upload.
"""
from typing import List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from config.constants import ConflictPolicy
from app.services.file_service import FileTask
from app.utils.formatters import format_bytes


class PushSummaryDialog(QDialog):
    """Confirmation and summary dialog before pushing files to Google Drive."""

    def __init__(
        self,
        tasks: List[FileTask],
        destination_name: str,
        destination_path: str,
        destination_id: str,
        default_policy: str = ConflictPolicy.KEEP_BOTH,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle("Push to Google Drive - Summary")
        self.setMinimumWidth(500)
        self.setModal(True)

        self.tasks = tasks
        self.destination_name = destination_name
        self.destination_path = destination_path
        self.destination_id = destination_id
        self.selected_policy = default_policy

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        title = QLabel("🚀 Upload Summary")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(title)

        # Summary Card
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        # 1. Destination
        dest_title = QLabel("🎯 Google Drive Destination:")
        dest_title.setStyleSheet("font-weight: bold; color: #94a3b8;")
        card_layout.addWidget(dest_title)

        dest_val = QLabel(f"<b>{self.destination_path}</b>")
        dest_val.setStyleSheet("font-size: 14px; color: #f8fafc;")
        card_layout.addWidget(dest_val)

        id_val = QLabel(f"Folder ID: <span style='color: #64748b;'>{self.destination_id}</span>")
        id_val.setStyleSheet("font-size: 11px;")
        card_layout.addWidget(id_val)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #334155;")
        card_layout.addWidget(divider)

        # 2. File stats
        total_files = len(self.tasks)
        total_bytes = sum(t.file_size for t in self.tasks)

        stats_layout = QHBoxLayout()

        files_label = QLabel(f"📄 Total Files: <b>{total_files:,}</b>")
        files_label.setStyleSheet("color: #f8fafc; font-size: 13px;")
        stats_layout.addWidget(files_label)

        size_label = QLabel(f"💾 Total Size: <b>{format_bytes(total_bytes)}</b>")
        size_label.setStyleSheet("color: #f8fafc; font-size: 13px;")
        stats_layout.addWidget(size_label)

        card_layout.addLayout(stats_layout)
        layout.addWidget(card)

        # 3. Conflict Policy Selector
        policy_box = QVBoxLayout()
        policy_label = QLabel("Duplicate File Policy:")
        policy_label.setStyleSheet("font-weight: 600; color: #f8fafc;")
        policy_box.addWidget(policy_label)

        self.policy_combo = QComboBox()
        for code, label in ConflictPolicy.CHOICES:
            self.policy_combo.addItem(label, code)

        idx = self.policy_combo.findData(self.selected_policy)
        if idx >= 0:
            self.policy_combo.setCurrentIndex(idx)
        policy_box.addWidget(self.policy_combo)
        layout.addLayout(policy_box)

        # 4. Confirmation Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.start_btn = QPushButton("Start Upload (Push Now)")
        self.start_btn.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-size: 13px;
            font-weight: bold;
            padding: 9px 20px;
            border-radius: 6px;
        """)
        self.start_btn.clicked.connect(self._accept_with_policy)
        btn_layout.addWidget(self.start_btn)

        layout.addLayout(btn_layout)

    def _accept_with_policy(self):
        self.selected_policy = self.policy_combo.currentData()
        self.accept()

    def get_conflict_policy(self) -> str:
        return self.selected_policy
