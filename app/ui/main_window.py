"""
Main Application Window for Google Drive AutoPush.
Coordinates sidebar navigation, page views, system notifications, and global state.
"""
from typing import Dict
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from config.constants import APP_NAME, APP_VERSION
from config.settings import AppSettings
from app.core.signals import signal_bus
from app.database.db_manager import DatabaseManager
from app.services.auth_service import AuthService
from app.services.drive_service import DriveService
from app.services.sync_service import SyncService
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.destination_page import DestinationPage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.sync_page import SyncPage
from app.ui.pages.upload_page import UploadPage
from app.utils.logger import logger


class MainWindow(QMainWindow):
    """Primary Desktop Application Window."""

    def __init__(
        self,
        auth_service: AuthService,
        drive_service: DriveService,
        sync_service: SyncService,
        db_manager: DatabaseManager,
        app_settings: AppSettings
    ):
        super().__init__()
        self.auth_service = auth_service
        self.drive_service = drive_service
        self.sync_service = sync_service
        self.db_manager = db_manager
        self.app_settings = app_settings

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)

        self._nav_buttons: Dict[str, QPushButton] = {}
        self._init_ui()
        self._connect_signals()

        # Try to restore session on startup
        self._initialize_startup_auth()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 16, 12, 16)
        sb_layout.setSpacing(6)

        # Header: Logo & Title
        header_box = QVBoxLayout()
        header_box.setSpacing(2)

        logo_title = QLabel("☁️ AutoPush")
        logo_title.setObjectName("appLogoTitle")
        header_box.addWidget(logo_title)

        version_label = QLabel(f"Google Drive AutoPush v{APP_VERSION}")
        version_label.setObjectName("appVersionLabel")
        header_box.addWidget(version_label)
        sb_layout.addLayout(header_box)

        # Divider
        sb_layout.addSpacing(10)
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("color: #334155;")
        sb_layout.addWidget(div)
        sb_layout.addSpacing(10)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("upload", "⬆️  Upload Files"),
            ("destinations", "📁  Destinations & Folders"),
            ("sync", "🔄  Auto Sync"),
            ("history", "📜  Upload History"),
            ("settings", "⚙️  Settings"),
        ]

        for page_id, label in nav_items:
            btn = QPushButton(label)
            btn.setProperty("class", "nav-btn")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, pid=page_id: self.navigate_to(pid))
            self.nav_group.addButton(btn)
            self._nav_buttons[page_id] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Bottom Connection Status Card in Sidebar
        status_box = QFrame()
        status_box.setStyleSheet("background-color: #0f172a; border-radius: 8px; padding: 10px;")
        sb_status_layout = QVBoxLayout(status_box)
        sb_status_layout.setSpacing(4)

        self.sb_conn_indicator = QLabel("🔴 Offline")
        self.sb_conn_indicator.setStyleSheet("font-size: 11px; font-weight: bold; color: #ef4444;")
        sb_status_layout.addWidget(self.sb_conn_indicator)

        self.sb_user_label = QLabel("Not connected")
        self.sb_user_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        sb_status_layout.addWidget(self.sb_user_label)

        sb_layout.addWidget(status_box)
        root_layout.addWidget(sidebar)

        # 2. Main Content Area (StackedWidget)
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentArea")

        # Initialize Pages
        self.page_dashboard = DashboardPage(self.auth_service, self.db_manager)
        self.page_dashboard.navigate_requested.connect(self.navigate_to)
        self.content_stack.addWidget(self.page_dashboard)  # Index 0

        self.page_upload = UploadPage(self.drive_service, self.db_manager)
        self.page_upload.change_dest_btn.clicked.connect(lambda: self.navigate_to("destinations"))
        self.content_stack.addWidget(self.page_upload)  # Index 1

        self.page_destinations = DestinationPage(self.drive_service, self.db_manager)
        self.content_stack.addWidget(self.page_destinations)  # Index 2

        self.page_sync = SyncPage(self.sync_service, self.db_manager)
        self.content_stack.addWidget(self.page_sync)  # Index 3

        self.page_history = HistoryPage(self.db_manager)
        self.content_stack.addWidget(self.page_history)  # Index 4

        self.page_settings = SettingsPage(self.auth_service, self.app_settings)
        self.content_stack.addWidget(self.page_settings)  # Index 5

        root_layout.addWidget(self.content_stack)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setStyleSheet("background-color: #0f172a; color: #64748b; font-size: 11px;")
        self.status_bar.showMessage("Ready")

        # Default navigation to Dashboard
        self.navigate_to("dashboard")

    def _connect_signals(self):
        signal_bus.auth_status_changed.connect(self._on_auth_status_changed)
        signal_bus.show_notification.connect(self._on_notification)
        signal_bus.destination_selected.connect(self._on_destination_selected)

    def _initialize_startup_auth(self):
        """Attempts to restore previous session from token.json."""
        logger.info("Initializing session check on startup...")
        if self.auth_service.initialize_session():
            profile = self.auth_service.get_user_profile()
            signal_bus.auth_status_changed.emit(
                True,
                profile.get("display_name", ""),
                profile.get("email", ""),
                profile
            )

    def navigate_to(self, page_id: str):
        """Switches stacked widget view and toggles nav button."""
        mapping = {
            "dashboard": (0, self.page_dashboard),
            "upload": (1, self.page_upload),
            "destinations": (2, self.page_destinations),
            "sync": (3, self.page_sync),
            "history": (4, self.page_history),
            "settings": (5, self.page_settings),
        }
        if page_id in mapping:
            idx, page = mapping[page_id]
            self.content_stack.setCurrentIndex(idx)
            btn = self._nav_buttons.get(page_id)
            if btn:
                btn.setChecked(True)

            # Trigger refresh if page has it
            if page_id == "dashboard":
                self.page_dashboard.refresh_dashboard()
            elif page_id == "destinations":
                self.page_destinations.refresh_current_folder()
            elif page_id == "history":
                self.page_history.refresh_history()

    def _on_auth_status_changed(self, is_auth: bool, name: str, email: str, quota: dict):
        if is_auth:
            self.sb_conn_indicator.setText("🟢 Connected")
            self.sb_conn_indicator.setStyleSheet("font-size: 11px; font-weight: bold; color: #34d399;")
            self.sb_user_label.setText(email or name or "Google User")
            self.status_bar.showMessage(f"Connected to Google Drive as {email}", 5000)
            # Reset Drive service cache
            self.drive_service.reset_service()
        else:
            self.sb_conn_indicator.setText("🔴 Disconnected")
            self.sb_conn_indicator.setStyleSheet("font-size: 11px; font-weight: bold; color: #ef4444;")
            self.sb_user_label.setText("Not connected")
            self.status_bar.showMessage("Google Drive disconnected", 5000)

    def _on_notification(self, title: str, message: str, level: str):
        timeout = 6000
        prefix = "✅" if level == "success" else "⚠️" if level == "warning" else "❌" if level == "error" else "ℹ️"
        clean_msg = message.replace("\n", " - ")
        self.status_bar.showMessage(f"{prefix} [{title}] {clean_msg}", timeout)

    def _on_destination_selected(self, folder_id: str, folder_name: str, folder_path: str):
        self.status_bar.showMessage(f"Selected destination: {folder_path} (ID: {folder_id})", 4000)

    def closeEvent(self, event):
        """Clean shutdown of observers and workers."""
        logger.info("Application closing. Cleaning up resources...")
        self.sync_service.stop_all()
        event.accept()
