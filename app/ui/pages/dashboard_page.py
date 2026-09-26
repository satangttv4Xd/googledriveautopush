"""
Dashboard Page.
Provides overview of Google Drive account status, storage quota, upload statistics,
quick launch action cards, and recent upload activity.
"""
from typing import Any, Dict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.services.auth_service import AuthService
from app.utils.formatters import format_bytes, format_timestamp


class DashboardPage(QWidget):
    """Main overview dashboard."""

    navigate_requested = Signal(str)  # Target page name: 'upload', 'destinations', 'sync'

    def __init__(self, auth_service: AuthService, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.db_manager = db_manager

        self._init_ui()
        self._connect_signals()
        self.refresh_dashboard()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Top Row: Account Card & Storage Quota Card
        top_grid = QGridLayout()
        top_grid.setSpacing(16)

        # Account Status Card
        self.account_card = QFrame()
        self.account_card.setProperty("class", "card")
        acc_layout = QVBoxLayout(self.account_card)
        acc_layout.setSpacing(10)

        acc_title = QLabel("👤 Google Account")
        acc_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        acc_layout.addWidget(acc_title)

        self.account_status_label = QLabel("🔴 Disconnected")
        self.account_status_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #ef4444;")
        acc_layout.addWidget(self.account_status_label)

        self.account_name_label = QLabel("Not Signed In")
        self.account_name_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #f8fafc;")
        acc_layout.addWidget(self.account_name_label)

        self.account_email_label = QLabel("Please connect your Google Account in Settings.")
        self.account_email_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        acc_layout.addWidget(self.account_email_label)

        acc_btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect Google Drive")
        self.connect_btn.setProperty("class", "primary-btn")
        self.connect_btn.clicked.connect(lambda: self.navigate_requested.emit("settings"))
        acc_btn_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setProperty("class", "danger-btn")
        self.disconnect_btn.setVisible(False)
        self.disconnect_btn.clicked.connect(self._disconnect_account)
        acc_btn_row.addWidget(self.disconnect_btn)

        acc_layout.addLayout(acc_btn_row)
        top_grid.addWidget(self.account_card, 0, 0)

        # Storage Quota Card
        self.quota_card = QFrame()
        self.quota_card.setProperty("class", "card")
        q_layout = QVBoxLayout(self.quota_card)
        q_layout.setSpacing(10)

        q_title = QLabel("☁️ Google Drive Storage")
        q_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        q_layout.addWidget(q_title)

        self.quota_text_label = QLabel("0 GB used of 0 GB")
        self.quota_text_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #f8fafc;")
        q_layout.addWidget(self.quota_text_label)

        self.quota_bar = QProgressBar()
        self.quota_bar.setValue(0)
        q_layout.addWidget(self.quota_bar)

        self.quota_details_label = QLabel("Usage in Drive: 0 GB")
        self.quota_details_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        q_layout.addWidget(self.quota_details_label)

        top_grid.addWidget(self.quota_card, 0, 1)
        layout.addLayout(top_grid)

        # 2. Metric Cards Grid
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(14)

        self.card_total_files = self._create_metric_card("📄 Files Uploaded", "0")
        self.card_total_bytes = self._create_metric_card("💾 Data Transferred", "0 B")
        self.card_completed = self._create_metric_card("✅ Successful", "0", color="#34d399")
        self.card_failed = self._create_metric_card("❌ Failed / Retried", "0", color="#f87171")

        metrics_grid.addWidget(self.card_total_files, 0, 0)
        metrics_grid.addWidget(self.card_total_bytes, 0, 1)
        metrics_grid.addWidget(self.card_completed, 0, 2)
        metrics_grid.addWidget(self.card_failed, 0, 3)
        layout.addLayout(metrics_grid)

        # 3. Quick Action Buttons Card
        action_card = QFrame()
        action_card.setProperty("class", "card")
        act_layout = QHBoxLayout(action_card)
        act_layout.setSpacing(12)

        act_label = QLabel("⚡ Quick Actions:")
        act_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #94a3b8;")
        act_layout.addWidget(act_label)

        btn_push = QPushButton("⬆️ Upload Files (Push)")
        btn_push.setProperty("class", "primary-btn")
        btn_push.clicked.connect(lambda: self.navigate_requested.emit("upload"))
        act_layout.addWidget(btn_push)

        btn_dest = QPushButton("📁 Destination Manager (+ New Folder)")
        btn_dest.clicked.connect(lambda: self.navigate_requested.emit("destinations"))
        act_layout.addWidget(btn_dest)

        btn_sync = QPushButton("🔄 Auto Sync Manager")
        btn_sync.clicked.connect(lambda: self.navigate_requested.emit("sync"))
        act_layout.addWidget(btn_sync)

        act_layout.addStretch()
        layout.addWidget(action_card)

        # 4. Recent Activity Table
        rec_box = QVBoxLayout()
        rec_title = QLabel("🕒 Recent Upload Activity")
        rec_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f8fafc;")
        rec_box.addWidget(rec_title)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["Timestamp", "Filename", "Destination", "Size", "Status"])
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.recent_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.recent_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.recent_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.recent_table.setAlternatingRowColors(True)
        rec_box.addWidget(self.recent_table)

        layout.addLayout(rec_box)

    def _create_metric_card(self, title: str, initial_value: str, color: str = "#38bdf8") -> QFrame:
        card = QFrame()
        card.setProperty("class", "card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(6)

        t_label = QLabel(title)
        t_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        c_layout.addWidget(t_label)

        v_label = QLabel(initial_value)
        v_label.setObjectName("metric_value")
        v_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        c_layout.addWidget(v_label)
        return card

    def _connect_signals(self):
        signal_bus.auth_status_changed.connect(self._on_auth_changed)
        signal_bus.history_updated.connect(self.refresh_dashboard)

    def refresh_dashboard(self):
        """Refreshes account info, metrics, and recent table from DB and Auth."""
        is_auth = self.auth_service.is_authenticated()
        profile = self.auth_service.get_user_profile() if is_auth else {}
        self._update_auth_ui(is_auth, profile)

        # Update Metrics from Database
        stats = self.db_manager.get_history_stats()
        total_count = stats.get("total_count", 0)
        total_bytes = stats.get("total_bytes", 0)
        completed = stats.get("completed_count", 0)
        failed = stats.get("failed_count", 0)

        self._set_card_value(self.card_total_files, f"{total_count:,}")
        self._set_card_value(self.card_total_bytes, format_bytes(total_bytes))
        self._set_card_value(self.card_completed, f"{completed:,}")
        self._set_card_value(self.card_failed, f"{failed:,}")

        # Update Recent Table
        recent = self.db_manager.get_history(limit=5)
        self.recent_table.setRowCount(len(recent))
        for row, item in enumerate(recent):
            self.recent_table.setItem(row, 0, QTableWidgetItem(format_timestamp(item.timestamp)))
            self.recent_table.setItem(row, 1, QTableWidgetItem(item.filename))
            self.recent_table.setItem(row, 2, QTableWidgetItem(item.drive_folder_path))
            self.recent_table.setItem(row, 3, QTableWidgetItem(format_bytes(item.file_size)))

            status_badge = QLabel(f" {item.status.upper()} ")
            if item.status == "completed":
                status_badge.setProperty("class", "badge badge-success")
            elif item.status == "skipped":
                status_badge.setProperty("class", "badge badge-warning")
            else:
                status_badge.setProperty("class", "badge badge-danger")
            status_badge.setAlignment(Qt.AlignCenter)
            self.recent_table.setCellWidget(row, 4, status_badge)

    def _set_card_value(self, card: QFrame, val: str):
        label = card.findChild(QLabel, "metric_value")
        if label:
            label.setText(val)

    def _on_auth_changed(self, is_auth: bool, name: str, email: str, quota: Any):
        profile = {
            "display_name": name,
            "email": email,
            "quota_limit": quota.get("limit", 0) if isinstance(quota, dict) else 0,
            "quota_usage": quota.get("usage", 0) if isinstance(quota, dict) else 0,
            "quota_usage_in_drive": quota.get("usageInDrive", 0) if isinstance(quota, dict) else 0,
        }
        self._update_auth_ui(is_auth, profile)

    def _update_auth_ui(self, is_auth: bool, profile: Dict[str, Any]):
        if is_auth:
            self.account_status_label.setText("🟢 Connected")
            self.account_status_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #34d399;")
            self.account_name_label.setText(profile.get("display_name", "Google Account"))
            self.account_email_label.setText(profile.get("email", ""))
            self.connect_btn.setVisible(False)
            self.disconnect_btn.setVisible(True)

            # Quota
            limit = profile.get("quota_limit", 0)
            usage = profile.get("quota_usage", 0)
            drive_usage = profile.get("quota_usage_in_drive", 0)

            if limit > 0:
                pct = int((usage / limit) * 100)
                self.quota_bar.setValue(pct)
                self.quota_text_label.setText(f"{format_bytes(usage)} used of {format_bytes(limit)} ({pct}%)")
            else:
                self.quota_bar.setValue(0)
                self.quota_text_label.setText(f"{format_bytes(usage)} used (Unlimited)")

            self.quota_details_label.setText(f"Usage specifically in Drive: {format_bytes(drive_usage)}")
        else:
            self.account_status_label.setText("🔴 Disconnected")
            self.account_status_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #ef4444;")
            self.account_name_label.setText("Not Signed In")
            self.account_email_label.setText("Please connect your Google Account in Settings.")
            self.connect_btn.setVisible(True)
            self.disconnect_btn.setVisible(False)
            self.quota_bar.setValue(0)
            self.quota_text_label.setText("0 B used of 0 B")
            self.quota_details_label.setText("Usage in Drive: 0 B")

    def _disconnect_account(self):
        self.auth_service.logout()
        signal_bus.auth_status_changed.emit(False, "", "", {})
        self.refresh_dashboard()
