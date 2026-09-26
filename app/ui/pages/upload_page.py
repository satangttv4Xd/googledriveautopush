"""
Upload Files Page.
Select files/folders, drag & drop, review totals, configure conflict policy,
and run multi-file resumable uploads with live progress, speed, ETA, pause, resume, and cancel.
"""
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.constants import ConflictPolicy, FolderUploadMode, UploadStatus
from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.services.drive_service import DriveService
from app.services.file_service import FileService, FileTask
from app.ui.dialogs.summary_dialog import PushSummaryDialog
from app.utils.formatters import format_bytes, format_eta, format_speed
from app.utils.logger import logger
from app.workers.upload_worker import UploadWorker


class DropAreaWidget(QFrame):
    """Drag-and-drop zone accepting both individual files and directories."""
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        icon_label = QLabel("📥")
        icon_label.setStyleSheet("font-size: 28px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        text_label = QLabel("Drag & Drop Files or Folders Here")
        text_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        text_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(text_label)

        sub_label = QLabel("Or use the buttons above to browse your computer")
        sub_label.setStyleSheet("font-size: 11px; color: #64748b;")
        sub_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub_label)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("border-color: #3b82f6; background-color: #1e3a8a;")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()


class UploadPage(QWidget):
    """File upload queue and active transfer manager."""

    def __init__(self, drive_service: DriveService, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.db_manager = db_manager

        self.tasks: List[FileTask] = []
        self._target_folder_id = "root"
        self._target_folder_path = "My Drive"
        self._target_folder_name = "My Drive"
        self._conflict_policy = ConflictPolicy.KEEP_BOTH

        self._upload_worker: Optional[UploadWorker] = None
        self._is_uploading = False

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Target Destination Card
        dest_card = QFrame()
        dest_card.setProperty("class", "card")
        dest_layout = QHBoxLayout(dest_card)
        dest_layout.setContentsMargins(16, 12, 16, 12)

        info_box = QVBoxLayout()
        dest_title = QLabel("🎯 Google Drive Destination:")
        dest_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
        info_box.addWidget(dest_title)

        self.dest_label = QLabel(f"<b>{self._target_folder_path}</b> (ID: {self._target_folder_id})")
        self.dest_label.setStyleSheet("font-size: 14px; color: #38bdf8;")
        info_box.addWidget(self.dest_label)
        dest_layout.addLayout(info_box)

        dest_layout.addStretch()

        self.change_dest_btn = QPushButton("📁 Browse / Change Destination")
        self.change_dest_btn.setToolTip("Switch to Destination Manager to create or choose a folder")
        dest_layout.addWidget(self.change_dest_btn)
        layout.addWidget(dest_card)

        # 2. File Selection Toolbar & Drop Zone
        tools_layout = QHBoxLayout()

        self.add_files_btn = QPushButton("📄 Add Files...")
        self.add_files_btn.setProperty("class", "primary-btn")
        self.add_files_btn.clicked.connect(self._select_files)
        tools_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("📁 Add Folder...")
        self.add_folder_btn.clicked.connect(self._select_folder)
        tools_layout.addWidget(self.add_folder_btn)

        self.clear_btn = QPushButton("🗑 Clear All")
        self.clear_btn.clicked.connect(self._clear_all)
        tools_layout.addWidget(self.clear_btn)

        tools_layout.addStretch()

        # Policy selector shortcut
        tools_layout.addWidget(QLabel("Policy:"))
        self.policy_combo = QComboBox()
        for code, label in ConflictPolicy.CHOICES:
            self.policy_combo.addItem(label, code)
        self.policy_combo.setCurrentIndex(2)  # Default: Keep Both
        self.policy_combo.currentIndexChanged.connect(self._on_policy_changed)
        tools_layout.addWidget(self.policy_combo)

        layout.addLayout(tools_layout)

        # Drag and Drop Box
        self.drop_area = DropAreaWidget()
        self.drop_area.files_dropped.connect(self._handle_dropped_paths)
        layout.addWidget(self.drop_area)

        # 3. Files Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Filename", "Relative Path", "Size", "Type", "Remove"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # 4. Active Progress Panel
        self.progress_panel = QFrame()
        self.progress_panel.setProperty("class", "card")
        p_layout = QVBoxLayout(self.progress_panel)
        p_layout.setSpacing(8)

        # Overall progress
        self.overall_label = QLabel("Overall Progress: 0 / 0 files (0 B / 0 B)")
        self.overall_label.setStyleSheet("font-weight: bold; color: #f8fafc;")
        p_layout.addWidget(self.overall_label)

        self.overall_bar = QProgressBar()
        self.overall_bar.setValue(0)
        p_layout.addWidget(self.overall_bar)

        # Current file progress & stats
        stat_row = QHBoxLayout()
        self.file_label = QLabel("Current File: Idle")
        self.file_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        stat_row.addWidget(self.file_label)

        stat_row.addStretch()

        self.speed_label = QLabel("Speed: 0 KB/s")
        self.speed_label.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        stat_row.addWidget(self.speed_label)

        self.eta_label = QLabel("ETA: --:--")
        self.eta_label.setStyleSheet("color: #fbbf24; font-weight: bold; font-size: 12px;")
        stat_row.addWidget(self.eta_label)

        p_layout.addLayout(stat_row)

        self.file_bar = QProgressBar()
        self.file_bar.setValue(0)
        p_layout.addWidget(self.file_bar)

        layout.addWidget(self.progress_panel)

        # 5. Bottom Controls (Totals & Push Button)
        bottom_row = QHBoxLayout()

        self.totals_label = QLabel("📄 0 files | 💾 0 B")
        self.totals_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        bottom_row.addWidget(self.totals_label)

        bottom_row.addStretch()

        # Pause / Resume / Cancel Controls
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setVisible(False)
        self.pause_btn.clicked.connect(self._toggle_pause)
        bottom_row.addWidget(self.pause_btn)

        self.cancel_btn = QPushButton("⏹ Cancel")
        self.cancel_btn.setProperty("class", "danger-btn")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self._cancel_upload)
        bottom_row.addWidget(self.cancel_btn)

        # Main Push Button
        self.push_btn = QPushButton("🚀 Push to Google Drive")
        self.push_btn.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-size: 14px;
            font-weight: bold;
            padding: 10px 24px;
            border-radius: 8px;
        """)
        self.push_btn.clicked.connect(self._confirm_and_push)
        bottom_row.addWidget(self.push_btn)

        layout.addLayout(bottom_row)

    def _connect_signals(self):
        signal_bus.destination_selected.connect(self.set_destination)
        signal_bus.upload_batch_started.connect(self._on_batch_started)
        signal_bus.upload_file_progress.connect(self._on_file_progress)
        signal_bus.upload_overall_progress.connect(self._on_overall_progress)
        signal_bus.upload_file_completed.connect(self._on_file_completed)
        signal_bus.upload_file_failed.connect(self._on_file_failed)
        signal_bus.upload_batch_finished.connect(self._on_batch_finished)

    def set_destination(self, folder_id: str, folder_name: str, folder_path: str):
        """Updates upload target destination."""
        self._target_folder_id = folder_id
        self._target_folder_name = folder_name
        self._target_folder_path = folder_path
        self.dest_label.setText(f"<b>{folder_path}</b> (ID: {folder_id})")

    # ================= FILE SELECTION =================

    def _select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Upload")
        if files:
            for f in files:
                task = FileService.get_file_task(f)
                if task:
                    self.tasks.append(task)
            self._update_table()

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder to Upload")
        if not folder:
            return

        # Prompt user: Upload Contents vs Upload As Folder
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Folder Upload Mode")
        msg_box.setText(f"How would you like to upload folder:\n'{Path(folder).name}'?")
        
        btn_as_folder = msg_box.addButton("Upload As Folder (Create new folder on Drive)", QMessageBox.AcceptRole)
        btn_contents = msg_box.addButton("Upload Contents (Files & subfolders directly)", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.exec()

        if msg_box.clickedButton() == btn_cancel:
            return

        mode = FolderUploadMode.AS_FOLDER if msg_box.clickedButton() == btn_as_folder else FolderUploadMode.CONTENTS_ONLY
        tasks = FileService.scan_folder(folder, upload_mode=mode)
        self.tasks.extend(tasks)
        self._update_table()

    def _handle_dropped_paths(self, paths: List[str]):
        """Processes files and folders dropped into the window."""
        for p in paths:
            path_obj = Path(p)
            if path_obj.is_file():
                task = FileService.get_file_task(p)
                if task:
                    self.tasks.append(task)
            elif path_obj.is_dir():
                # Default dropped folder to Upload As Folder
                tasks = FileService.scan_folder(p, upload_mode=FolderUploadMode.AS_FOLDER)
                self.tasks.extend(tasks)
        self._update_table()

    def _update_table(self):
        self.table.setRowCount(len(self.tasks))
        for row, t in enumerate(self.tasks):
            self.table.setItem(row, 0, QTableWidgetItem(t.filename))
            self.table.setItem(row, 1, QTableWidgetItem(t.relative_path))
            self.table.setItem(row, 2, QTableWidgetItem(format_bytes(t.file_size)))
            self.table.setItem(row, 3, QTableWidgetItem(t.file_type))

            rm_btn = QPushButton("✕")
            rm_btn.setProperty("class", "icon-btn")
            rm_btn.clicked.connect(lambda _, r=row: self._remove_task(r))
            self.table.setCellWidget(row, 4, rm_btn)

        total_files, total_bytes = FileService.calculate_totals(self.tasks)
        self.totals_label.setText(f"📄 {total_files:,} files | 💾 {format_bytes(total_bytes)}")
        self.push_btn.setEnabled(total_files > 0 and not self._is_uploading)

    def _remove_task(self, row_idx: int):
        if 0 <= row_idx < len(self.tasks):
            del self.tasks[row_idx]
            self._update_table()

    def _clear_all(self):
        if not self._is_uploading:
            self.tasks.clear()
            self._update_table()

    def _on_policy_changed(self):
        self._conflict_policy = self.policy_combo.currentData()

    # ================= PUSH / UPLOAD EXECUTION =================

    def _confirm_and_push(self):
        if not self.tasks:
            QMessageBox.warning(self, "No Files", "Please add files or folders to upload first.")
            return

        if not self.drive_service.auth_service.is_authenticated():
            QMessageBox.warning(self, "Not Connected", "Please connect to Google Drive first.")
            return

        # Show Pre-Push Summary Dialog
        dialog = PushSummaryDialog(
            tasks=self.tasks,
            destination_name=self._target_folder_name,
            destination_path=self._target_folder_path,
            destination_id=self._target_folder_id,
            default_policy=self._conflict_policy,
            parent=self
        )
        if dialog.exec() == PushSummaryDialog.Accepted:
            self._conflict_policy = dialog.get_conflict_policy()
            self._start_upload_worker()

    def _start_upload_worker(self):
        self._is_uploading = True
        self.push_btn.setEnabled(False)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)

        self.pause_btn.setVisible(True)
        self.pause_btn.setText("⏸ Pause")
        self.cancel_btn.setVisible(True)

        self._upload_worker = UploadWorker(
            drive_service=self.drive_service,
            db_manager=self.db_manager,
            tasks=list(self.tasks),
            destination_folder_id=self._target_folder_id,
            destination_path=self._target_folder_path,
            conflict_policy=self._conflict_policy,
            parent=self
        )
        self._upload_worker.start()

    def _toggle_pause(self):
        if not self._upload_worker:
            return
        if self._upload_worker._is_paused:
            self._upload_worker.resume()
            self.pause_btn.setText("⏸ Pause")
        else:
            self._upload_worker.pause()
            self.pause_btn.setText("▶ Resume")

    def _cancel_upload(self):
        if self._upload_worker:
            reply = QMessageBox.question(
                self,
                "Cancel Upload",
                "Are you sure you want to cancel the upload?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self._upload_worker.cancel()

    # ================= WORKER SIGNAL HANDLERS =================

    def _on_batch_started(self, total_files: int, total_bytes: int):
        self.overall_label.setText(f"Overall Progress: 0 / {total_files} files (0 B / {format_bytes(total_bytes)})")
        self.overall_bar.setValue(0)
        self.file_bar.setValue(0)

    def _on_file_progress(self, filename: str, bytes_sent: int, file_size: int, speed: float, eta: float):
        self.file_label.setText(f"Current File: {filename} ({format_bytes(bytes_sent)} / {format_bytes(file_size)})")
        pct = int((bytes_sent / file_size) * 100) if file_size > 0 else 100
        self.file_bar.setValue(pct)
        self.speed_label.setText(f"Speed: {format_speed(speed)}")
        self.eta_label.setText(f"ETA: {format_eta(eta)}")

    def _on_overall_progress(self, done_files: int, total_files: int, done_bytes: int, total_bytes: int, speed: float, eta: float):
        pct = int((done_bytes / total_bytes) * 100) if total_bytes > 0 else 100
        self.overall_bar.setValue(pct)
        self.overall_label.setText(
            f"Overall Progress: {done_files} / {total_files} files ({format_bytes(done_bytes)} / {format_bytes(total_bytes)}) - {pct}%"
        )

    def _on_file_completed(self, filename: str, drive_id: str, status: str):
        logger.debug(f"File upload status: {filename} -> {status}")

    def _on_file_failed(self, filename: str, err: str):
        logger.error(f"File failed: {filename}: {err}")

    def _on_batch_finished(self, completed: int, failed: int, skipped: int):
        self._is_uploading = False
        self.push_btn.setEnabled(True)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.pause_btn.setVisible(False)
        self.cancel_btn.setVisible(False)

        self.speed_label.setText("Speed: 0 KB/s")
        self.eta_label.setText("ETA: 00:00")
        self.file_label.setText("Upload Finished.")

        # Show notification or message
        msg = f"Push finished!\nCompleted: {completed}\nFailed: {failed}\nSkipped: {skipped}"
        signal_bus.show_notification.emit("Upload Batch Finished", msg, "success" if failed == 0 else "warning")
        QMessageBox.information(self, "Upload Complete", msg)

        # Clear successfully uploaded items
        self.tasks.clear()
        self._update_table()
