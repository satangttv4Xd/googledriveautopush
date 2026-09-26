"""
Auto-Sync Manager Page.
Configures and monitors local directory watchers with Watchdog,
debounces file writing events, and manages automated Google Drive background uploads.
"""
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.database.models import SyncJobConfig
from app.services.sync_service import SyncService
from app.ui.dialogs.add_sync_dialog import AddSyncJobDialog
from app.utils.formatters import format_timestamp
from app.utils.logger import logger


class SyncPage(QWidget):
    """Synchronization configurations and active watcher monitors."""

    def __init__(
        self,
        sync_service: SyncService,
        db_manager: DatabaseManager,
        current_dest_id: str = "root",
        current_dest_path: str = "My Drive",
        parent=None
    ):
        super().__init__(parent)
        self.sync_service = sync_service
        self.db_manager = db_manager
        self.current_dest_id = current_dest_id
        self.current_dest_path = current_dest_path

        self.sync_configs: List[SyncJobConfig] = []
        self._init_ui()
        self._connect_signals()
        self.load_sync_jobs()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Header Banner & Global Controls
        banner = QFrame()
        banner.setProperty("class", "card")
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(16, 12, 16, 12)

        info_box = QVBoxLayout()
        title = QLabel("🔄 Auto-Sync Manager")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        info_box.addWidget(title)

        desc = QLabel("Automatically monitor local computer folders and push changed or new files to Google Drive in the background.")
        desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        info_box.addWidget(desc)
        b_layout.addLayout(info_box)

        b_layout.addStretch()

        self.add_job_btn = QPushButton("➕ Add Sync Job")
        self.add_job_btn.setStyleSheet("""
            background-color: #2563eb;
            color: #ffffff;
            font-weight: bold;
            padding: 8px 18px;
            border-radius: 6px;
        """)
        self.add_job_btn.clicked.connect(self._open_add_job_dialog)
        b_layout.addWidget(self.add_job_btn)

        layout.addWidget(banner)

        # 2. Safety Notice Card
        notice = QFrame()
        notice.setProperty("class", "card")
        n_layout = QHBoxLayout(notice)
        n_layout.setContentsMargins(12, 8, 12, 8)

        notice_icon = QLabel("🛡️")
        notice_icon.setStyleSheet("font-size: 18px;")
        n_layout.addWidget(notice_icon)

        notice_text = QLabel("<b>Write-Lock Protection:</b> AutoPush checks file stability before queuing uploads to prevent corrupt or incomplete transfers. Local file deletions will <u>never</u> delete files in Google Drive.")
        notice_text.setStyleSheet("color: #34d399; font-size: 11px;")
        notice_text.setWordWrap(True)
        n_layout.addWidget(notice_text)
        layout.addWidget(notice)

        # 3. Sync Jobs Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Job Name", "Local Folder", "Drive Target", "Sync Modified", "Status", "Last Synced", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Status Footer
        self.status_label = QLabel("0 active sync watchers running.")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _connect_signals(self):
        signal_bus.destination_selected.connect(self._on_destination_updated)
        signal_bus.sync_jobs_updated.connect(self.load_sync_jobs)

    def _on_destination_updated(self, fid: str, fname: str, fpath: str):
        self.current_dest_id = fid
        self.current_dest_path = fpath

    def load_sync_jobs(self):
        """Loads sync configurations from SQLite and updates table and watchers."""
        self.sync_configs = self.db_manager.get_sync_configs()
        self.table.setRowCount(len(self.sync_configs))

        active_count = 0
        for row, job in enumerate(self.sync_configs):
            self.table.setItem(row, 0, QTableWidgetItem(job.name))
            self.table.setItem(row, 1, QTableWidgetItem(job.local_dir))
            self.table.setItem(row, 2, QTableWidgetItem(f"{job.drive_folder_path}"))
            self.table.setItem(row, 3, QTableWidgetItem("Yes" if job.sync_modified else "New Only"))

            # Status Badge
            is_running = self.sync_service.is_job_running(job.id)
            if job.is_active and is_running:
                active_count += 1
                status_label = QLabel(" RUNNING ")
                status_label.setProperty("class", "badge badge-success")
            elif job.is_active and not is_running:
                status_label = QLabel(" STARTING ")
                status_label.setProperty("class", "badge badge-warning")
            else:
                status_label = QLabel(" PAUSED ")
                status_label.setProperty("class", "badge badge-danger")
            status_label.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, status_label)

            self.table.setItem(row, 5, QTableWidgetItem(format_timestamp(job.last_synced) if job.last_synced else "Never"))

            # Actions layout
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)

            toggle_btn = QPushButton("Pause" if job.is_active else "Start")
            toggle_btn.setProperty("class", "icon-btn")
            toggle_btn.clicked.connect(lambda _, j=job: self._toggle_job_active(j))
            act_layout.addWidget(toggle_btn)

            del_btn = QPushButton("✕")
            del_btn.setProperty("class", "icon-btn danger-btn")
            del_btn.setToolTip("Delete sync job")
            del_btn.clicked.connect(lambda _, jid=job.id: self._delete_job(jid))
            act_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 6, actions_widget)

            # Auto-start active jobs in sync service if not already running
            if job.is_active and not is_running:
                self.sync_service.start_job(job)

        self.status_label.setText(f"{active_count} active sync watchers running.")

    def _open_add_job_dialog(self):
        dialog = AddSyncJobDialog(
            current_dest_id=self.current_dest_id,
            current_dest_path=self.current_dest_path,
            parent=self
        )
        if dialog.exec() == AddSyncJobDialog.Accepted:
            new_job = dialog.get_sync_config()
            job_id = self.db_manager.add_sync_config(new_job)
            new_job.id = job_id
            self.sync_service.start_job(new_job)
            self.load_sync_jobs()
            signal_bus.show_notification.emit(
                "Sync Job Created",
                f"Sync job '{new_job.name}' started.",
                "success"
            )

    def _toggle_job_active(self, job: SyncJobConfig):
        new_active = not job.is_active
        self.db_manager.update_sync_status(job.id, new_active)
        if new_active:
            self.sync_service.start_job(job)
        else:
            self.sync_service.stop_job(job.id)
        self.load_sync_jobs()

    def _delete_job(self, job_id: int):
        reply = QMessageBox.question(
            self,
            "Delete Sync Job",
            "Are you sure you want to delete this sync job?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.sync_service.stop_job(job_id)
            self.db_manager.delete_sync_config(job_id)
            self.load_sync_jobs()
