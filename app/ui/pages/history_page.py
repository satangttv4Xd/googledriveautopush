"""
Upload History Page.
Searchable, filterable audit log of past uploads stored in SQLite,
with detailed error inspection modal and CSV export.
"""
import csv
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.database.models import UploadHistoryItem
from app.ui.dialogs.error_dialog import ErrorDetailDialog
from app.utils.formatters import format_bytes, format_speed, format_timestamp


class HistoryPage(QWidget):
    """Historical record view of all file transfers."""

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.history_records: List[UploadHistoryItem] = []

        self._init_ui()
        self._connect_signals()
        self.refresh_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Search & Filter Bar
        toolbar = QFrame()
        toolbar.setProperty("class", "card")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel("🔍 Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by filename or destination path...")
        self.search_edit.textChanged.connect(self.refresh_history)
        tb_layout.addWidget(self.search_edit)

        tb_layout.addWidget(QLabel("Status:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Completed", "Failed", "Skipped"])
        self.filter_combo.currentIndexChanged.connect(self.refresh_history)
        tb_layout.addWidget(self.filter_combo)

        tb_layout.addStretch()

        self.export_btn = QPushButton("💾 Export CSV")
        self.export_btn.clicked.connect(self._export_csv)
        tb_layout.addWidget(self.export_btn)

        self.clear_btn = QPushButton("🗑 Clear History")
        self.clear_btn.setProperty("class", "danger-btn")
        self.clear_btn.clicked.connect(self._clear_history)
        tb_layout.addWidget(self.clear_btn)

        layout.addWidget(toolbar)

        # 2. History Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Timestamp", "Filename", "Destination", "Size", "Status", "Speed", "Duration", "Details"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

        # 3. Footer Stats
        self.stats_label = QLabel("Showing 0 records.")
        self.stats_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.stats_label)

    def _connect_signals(self):
        signal_bus.history_updated.connect(self.refresh_history)

    def refresh_history(self):
        """Queries SQLite and repopulates the table."""
        query = self.search_edit.text().strip()
        status = self.filter_combo.currentText()

        self.history_records = self.db_manager.get_history(
            search_query=query if query else None,
            status_filter=status if status != "All" else None,
            limit=200
        )

        self.table.setRowCount(len(self.history_records))
        for row, rec in enumerate(self.history_records):
            self.table.setItem(row, 0, QTableWidgetItem(format_timestamp(rec.timestamp)))
            self.table.setItem(row, 1, QTableWidgetItem(rec.filename))
            self.table.setItem(row, 2, QTableWidgetItem(rec.drive_folder_path))
            self.table.setItem(row, 3, QTableWidgetItem(format_bytes(rec.file_size)))

            # Status Badge
            badge = QLabel(f" {rec.status.upper()} ")
            if rec.status == "completed":
                badge.setProperty("class", "badge badge-success")
            elif rec.status == "skipped":
                badge.setProperty("class", "badge badge-warning")
            else:
                badge.setProperty("class", "badge badge-danger")
            badge.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 4, badge)

            self.table.setItem(row, 5, QTableWidgetItem(format_speed(rec.upload_speed)))
            self.table.setItem(row, 6, QTableWidgetItem(f"{rec.duration_seconds:.1f}s"))

            # Details Button
            if rec.error_message:
                detail_btn = QPushButton("View Error")
                detail_btn.setProperty("class", "icon-btn danger-btn")
                detail_btn.clicked.connect(lambda _, r=rec: self._show_error_dialog(r))
                self.table.setCellWidget(row, 7, detail_btn)
            else:
                self.table.setItem(row, 7, QTableWidgetItem("-"))

        self.stats_label.setText(f"Displaying {len(self.history_records)} records.")

    def _on_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.history_records):
            rec = self.history_records[row]
            if rec.error_message:
                self._show_error_dialog(rec)

    def _show_error_dialog(self, record: UploadHistoryItem):
        dialog = ErrorDetailDialog(
            filename=record.filename,
            error_message=record.error_message or "No details.",
            parent=self
        )
        dialog.exec()

    def _clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to permanently clear all upload history?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.db_manager.clear_history()
            self.refresh_history()

    def _export_csv(self):
        if not self.history_records:
            QMessageBox.information(self, "Export CSV", "No history records to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export History to CSV", "upload_history.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Filename", "Local Path", "Drive Folder Path", "Folder ID", "Size (Bytes)", "Status", "Speed (B/s)", "Duration (s)", "Error"])
                for r in self.history_records:
                    writer.writerow([
                        r.timestamp, r.filename, r.local_path, r.drive_folder_path,
                        r.drive_folder_id, r.file_size, r.status, r.upload_speed,
                        r.duration_seconds, r.error_message or ""
                    ])
            QMessageBox.information(self, "Export Successful", f"Saved history to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not write CSV: {e}")
