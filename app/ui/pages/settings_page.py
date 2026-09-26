"""
Application and Google Drive Settings Page.
Allows selecting credentials.json, initiating/terminating OAuth sessions,
configuring transfer defaults, and adjusting sync parameters.
"""
from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.constants import (
    DEFAULT_CREDENTIALS_PATH,
    ConflictPolicy,
)
from config.settings import AppSettings
from app.core.signals import signal_bus
from app.services.auth_service import AuthService
from app.utils.logger import logger
from app.workers.auth_worker import AuthWorker


class SettingsPage(QWidget):
    """Application preferences and OAuth management."""

    def __init__(self, auth_service: AuthService, app_settings: AppSettings, parent=None):
        super().__init__(parent)
        self.auth_service = auth_service
        self.app_settings = app_settings

        self._auth_worker: Optional[AuthWorker] = None
        self._init_ui()
        self._connect_signals()
        self.load_settings()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Google Drive OAuth Card
        oauth_card = QFrame()
        oauth_card.setProperty("class", "card")
        oa_layout = QVBoxLayout(oauth_card)
        oa_layout.setSpacing(12)

        oa_title = QLabel("🔑 Google Drive API Authentication")
        oa_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        oa_layout.addWidget(oa_title)

        oa_desc = QLabel(
            "To connect your Google Drive account, you need an OAuth 2.0 Client ID (credentials.json) "
            "created in your Google Cloud Console."
        )
        oa_desc.setWordWrap(True)
        oa_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        oa_layout.addWidget(oa_desc)

        # Credentials File Picker
        cred_row = QHBoxLayout()
        self.cred_path_edit = QLineEdit()
        self.cred_path_edit.setPlaceholderText("Path to credentials.json...")
        cred_row.addWidget(self.cred_path_edit)

        self.browse_cred_btn = QPushButton("Browse...")
        self.browse_cred_btn.clicked.connect(self._browse_credentials)
        cred_row.addWidget(self.browse_cred_btn)
        oa_layout.addLayout(cred_row)

        # Status & Connect / Disconnect Buttons
        btn_status_row = QHBoxLayout()

        self.auth_status_label = QLabel("Status: Disconnected")
        self.auth_status_label.setStyleSheet("font-weight: bold; color: #ef4444;")
        btn_status_row.addWidget(self.auth_status_label)

        btn_status_row.addStretch()

        self.connect_btn = QPushButton("Connect Google Drive")
        self.connect_btn.setProperty("class", "primary-btn")
        self.connect_btn.clicked.connect(self._start_oauth_login)
        btn_status_row.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect Account")
        self.disconnect_btn.setProperty("class", "danger-btn")
        self.disconnect_btn.clicked.connect(self._disconnect_account)
        self.disconnect_btn.setVisible(False)
        btn_status_row.addWidget(self.disconnect_btn)

        oa_layout.addLayout(btn_status_row)
        layout.addWidget(oauth_card)

        # 2. General Preferences Card
        pref_card = QFrame()
        pref_card.setProperty("class", "card")
        p_layout = QVBoxLayout(pref_card)
        p_layout.setSpacing(12)

        p_title = QLabel("⚙️ Transfer & Sync Preferences")
        p_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        p_layout.addWidget(p_title)

        form = QFormLayout()
        form.setSpacing(12)

        # Conflict policy
        self.policy_combo = QComboBox()
        for code, label in ConflictPolicy.CHOICES:
            self.policy_combo.addItem(label, code)
        form.addRow("Default Conflict Policy:", self.policy_combo)

        # Resumable Chunk Size
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1, 100)
        self.chunk_spin.setSuffix(" MB")
        self.chunk_spin.setValue(5)
        form.addRow("Upload Chunk Size:", self.chunk_spin)

        # Sync Debounce Seconds
        self.debounce_spin = QSpinBox()
        self.debounce_spin.setRange(1, 60)
        self.debounce_spin.setSuffix(" seconds")
        self.debounce_spin.setValue(5)
        form.addRow("Sync Debounce Interval:", self.debounce_spin)

        p_layout.addLayout(form)
        layout.addWidget(pref_card)

        # 3. Save Button Row
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self.save_btn = QPushButton("💾 Save Preferences")
        self.save_btn.setStyleSheet("""
            background-color: #059669;
            color: white;
            font-size: 13px;
            font-weight: bold;
            padding: 9px 22px;
            border-radius: 6px;
        """)
        self.save_btn.clicked.connect(self.save_settings)
        bottom_row.addWidget(self.save_btn)

        layout.addLayout(bottom_row)
        layout.addStretch()

    def _connect_signals(self):
        signal_bus.auth_status_changed.connect(self._on_auth_status_changed)

    def load_settings(self):
        """Populates UI from AppSettings."""
        saved_cred = self.app_settings.get("credentials_path", str(DEFAULT_CREDENTIALS_PATH))
        self.cred_path_edit.setText(saved_cred)

        saved_policy = self.app_settings.get("conflict_policy", ConflictPolicy.KEEP_BOTH)
        idx = self.policy_combo.findData(saved_policy)
        if idx >= 0:
            self.policy_combo.setCurrentIndex(idx)

        self.chunk_spin.setValue(self.app_settings.get_int("chunk_size_mb", 5))
        self.debounce_spin.setValue(self.app_settings.get_int("sync_debounce_seconds", 5))

        self._update_auth_ui(self.auth_service.is_authenticated())

    def save_settings(self):
        """Saves current UI values to AppSettings / DB."""
        cred_path = self.cred_path_edit.text().strip()
        policy = self.policy_combo.currentData()
        chunk = self.chunk_spin.value()
        debounce = self.debounce_spin.value()

        self.app_settings.set("credentials_path", cred_path)
        self.app_settings.set("conflict_policy", policy)
        self.app_settings.set("chunk_size_mb", chunk)
        self.app_settings.set("sync_debounce_seconds", debounce)

        # Update service credential path
        self.auth_service.credentials_path = Path(cred_path)

        signal_bus.show_notification.emit("Settings Saved", "Preferences saved successfully.", "success")
        QMessageBox.information(self, "Settings Saved", "Preferences have been saved.")

    def _browse_credentials(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select credentials.json", "", "JSON Files (*.json)")
        if file_path:
            self.cred_path_edit.setText(file_path)
            self.save_settings()

    def _start_oauth_login(self):
        cred_file = Path(self.cred_path_edit.text().strip())
        if not cred_file.exists():
            QMessageBox.warning(
                self,
                "Credentials Not Found",
                f"Cannot find credentials.json at:\n{cred_file}\n\n"
                "Please configure a valid credentials.json downloaded from Google Cloud Console."
            )
            return

        self.connect_btn.setEnabled(False)
        self.auth_status_label.setText("Status: Authorizing in browser...")
        self.auth_status_label.setStyleSheet("color: #fbbf24; font-weight: bold;")

        self._auth_worker = AuthWorker(self.auth_service, cred_file, parent=self)
        self._auth_worker.login_success.connect(self._on_login_success)
        self._auth_worker.login_failed.connect(self._on_login_failed)
        self._auth_worker.start()

    def _on_login_success(self, msg: str):
        self.connect_btn.setEnabled(True)
        self._update_auth_ui(True)
        profile = self.auth_service.get_user_profile()
        signal_bus.auth_status_changed.emit(
            True,
            profile.get("display_name", ""),
            profile.get("email", ""),
            profile
        )
        signal_bus.show_notification.emit("Connected", "Successfully connected to Google Drive!", "success")
        QMessageBox.information(self, "Google Drive Connected", "Your account is now connected and ready to push files.")

    def _on_login_failed(self, error: str):
        self.connect_btn.setEnabled(True)
        self._update_auth_ui(False)
        signal_bus.auth_status_changed.emit(False, "", "", {})
        logger.error(f"Login failed: {error}")
        QMessageBox.critical(self, "Connection Failed", f"Failed to connect Google Drive:\n{error}")

    def _disconnect_account(self):
        reply = QMessageBox.question(
            self,
            "Disconnect Account",
            "Are you sure you want to disconnect your Google account?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.auth_service.logout()
            self._update_auth_ui(False)
            signal_bus.auth_status_changed.emit(False, "", "", {})
            signal_bus.show_notification.emit("Disconnected", "Google Account disconnected.", "info")

    def _on_auth_status_changed(self, is_auth: bool, name: str, email: str, quota: dict):
        self._update_auth_ui(is_auth)

    def _update_auth_ui(self, is_auth: bool):
        if is_auth:
            profile = self.auth_service.get_user_profile()
            email = profile.get("email", "")
            self.auth_status_label.setText(f"Status: Connected ({email})")
            self.auth_status_label.setStyleSheet("color: #34d399; font-weight: bold;")
            self.connect_btn.setVisible(False)
            self.disconnect_btn.setVisible(True)
        else:
            self.auth_status_label.setText("Status: Disconnected")
            self.auth_status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.connect_btn.setVisible(True)
            self.disconnect_btn.setVisible(False)
