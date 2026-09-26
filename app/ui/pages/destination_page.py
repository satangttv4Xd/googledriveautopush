"""
Destination Manager Page.
Core Feature: Browse Google Drive folders, navigate hierarchies with breadcrumbs,
create new folders on Google Drive directly from within the app, and select target push destination.
"""
from typing import Any, Dict, List, Optional
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
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
from app.database.models import FolderBookmark
from app.services.drive_service import DriveService
from app.ui.dialogs.new_folder_dialog import NewFolderDialog
from app.utils.formatters import format_timestamp
from app.utils.logger import logger


class FolderLoaderWorker(QThread):
    """Background worker for fetching folder lists to prevent UI freezes."""
    folders_loaded = Signal(list)
    load_failed = Signal(str)

    def __init__(self, drive_service: DriveService, parent_id: str, parent=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.parent_id = parent_id

    def run(self):
        try:
            folders = self.drive_service.list_folders(self.parent_id)
            self.folders_loaded.emit(folders)
        except Exception as e:
            self.load_failed.emit(str(e))


class CreateFolderWorker(QThread):
    """Background worker for creating folders on Google Drive."""
    folder_created = Signal(dict)
    create_failed = Signal(str)

    def __init__(self, drive_service: DriveService, name: str, parent_id: str, parent=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.name = name
        self.parent_id = parent_id

    def run(self):
        try:
            if "/" in self.name or "\\" in self.name:
                folder = self.drive_service.create_folder_hierarchy(self.name, self.parent_id)
            else:
                folder = self.drive_service.create_folder(self.name, self.parent_id)
            self.folder_created.emit(folder)
        except Exception as e:
            self.create_failed.emit(str(e))


class DestinationPage(QWidget):
    """Destination Folder Manager for Google Drive."""

    def __init__(self, drive_service: DriveService, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.drive_service = drive_service
        self.db_manager = db_manager

        self.current_folder_id = "root"
        self.current_folder_name = "My Drive"
        self.breadcrumbs: List[tuple[str, str]] = [("root", "My Drive")]
        self.folders_cache: List[Dict[str, Any]] = []

        self._active_dest_id = "root"
        self._active_dest_path = "My Drive"

        self._loader_worker: Optional[FolderLoaderWorker] = None
        self._create_worker: Optional[CreateFolderWorker] = None

        self._init_ui()
        self._load_saved_destination()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Page Header & Active Destination Banner
        header_card = QFrame()
        header_card.setProperty("class", "card")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)

        info_box = QVBoxLayout()
        dest_title = QLabel("📍 Current Target Destination for Push:")
        dest_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #94a3b8;")
        info_box.addWidget(dest_title)

        self.active_dest_label = QLabel(f"<b>{self._active_dest_path}</b> (ID: {self._active_dest_id})")
        self.active_dest_label.setStyleSheet("font-size: 14px; color: #38bdf8; font-weight: bold;")
        info_box.addWidget(self.active_dest_label)
        header_layout.addLayout(info_box)

        header_layout.addStretch()

        self.set_dest_btn = QPushButton("🎯 Select Current Folder as Destination")
        self.set_dest_btn.setStyleSheet("""
            background-color: #059669;
            color: #ffffff;
            font-size: 13px;
            font-weight: bold;
            padding: 8px 18px;
            border-radius: 6px;
        """)
        self.set_dest_btn.setToolTip("Set the currently open Google Drive folder as target for file uploads.")
        self.set_dest_btn.clicked.connect(self._select_current_folder_as_destination)
        header_layout.addWidget(self.set_dest_btn)

        layout.addWidget(header_card)

        # 2. Toolbar & Navigation Row
        nav_card = QFrame()
        nav_card.setProperty("class", "card")
        nav_card_layout = QVBoxLayout(nav_card)
        nav_card_layout.setSpacing(10)

        # Row A: Action Buttons & Search
        tools_row = QHBoxLayout()

        self.back_btn = QPushButton("⬅ Back / Up")
        self.back_btn.setToolTip("Go up to parent folder")
        self.back_btn.clicked.connect(self._navigate_up)
        tools_row.addWidget(self.back_btn)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setToolTip("Fetch latest folders from Google Drive")
        self.refresh_btn.clicked.connect(self.refresh_current_folder)
        tools_row.addWidget(self.refresh_btn)

        # Prominent + New Folder Button
        self.new_folder_btn = QPushButton("➕ New Folder")
        self.new_folder_btn.setStyleSheet("""
            background-color: #2563eb;
            color: white;
            font-weight: bold;
            padding: 8px 16px;
            border-radius: 6px;
        """)
        self.new_folder_btn.setToolTip("Create a new folder directly in Google Drive")
        self.new_folder_btn.clicked.connect(self._open_new_folder_dialog)
        tools_row.addWidget(self.new_folder_btn)

        tools_row.addStretch()

        # Search filter
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Filter folders...")
        self.search_edit.setMaximumWidth(220)
        self.search_edit.textChanged.connect(self._filter_folders)
        tools_row.addWidget(self.search_edit)

        nav_card_layout.addLayout(tools_row)

        # Row B: Breadcrumb Navigation
        self.crumb_container = QWidget()
        self.crumb_layout = QHBoxLayout(self.crumb_container)
        self.crumb_layout.setContentsMargins(4, 4, 4, 4)
        self.crumb_layout.setSpacing(4)
        nav_card_layout.addWidget(self.crumb_container)

        layout.addWidget(nav_card)

        # 3. Folder Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Folder Name", "Folder ID", "Modified Time", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.table)

        # Status Footer
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(self.status_label)

    def _load_saved_destination(self):
        """Loads saved destination from database."""
        default_bm = None
        bookmarks = self.db_manager.get_folder_bookmarks()
        for bm in bookmarks:
            if bm.is_default:
                default_bm = bm
                break
        if default_bm:
            self._active_dest_id = default_bm.folder_id
            self._active_dest_path = default_bm.folder_path
        else:
            self._active_dest_id = "root"
            self._active_dest_path = "My Drive"
        self._update_active_dest_ui()

    def _update_active_dest_ui(self):
        self.active_dest_label.setText(f"<b>{self._active_dest_path}</b> (ID: {self._active_dest_id})")

    def refresh_current_folder(self):
        """Fetches folders inside current_folder_id from Google Drive."""
        if not self.drive_service.auth_service.is_authenticated():
            self.status_label.setText("Google Drive is not connected. Please connect first.")
            return

        self.status_label.setText(f"Loading folders in {self.current_folder_name}...")
        self.table.setRowCount(0)

        self._loader_worker = FolderLoaderWorker(self.drive_service, self.current_folder_id)
        self._loader_worker.folders_loaded.connect(self._on_folders_loaded)
        self._loader_worker.load_failed.connect(self._on_load_failed)
        self._loader_worker.start()

    def _on_folders_loaded(self, folders: List[Dict[str, Any]]):
        self.folders_cache = folders
        self._populate_table(folders)
        self._update_breadcrumbs()
        self.status_label.setText(f"Found {len(folders)} folders in {self.current_folder_name}.")

    def _on_load_failed(self, error: str):
        logger.error(f"Error loading folders: {error}")
        self.status_label.setText(f"Error loading folders: {error}")
        QMessageBox.warning(self, "Drive Error", f"Could not load folders: {error}")

    def _populate_table(self, folders: List[Dict[str, Any]]):
        self.table.setRowCount(len(folders))
        for row, f in enumerate(folders):
            name_item = QTableWidgetItem(f"📁  {f.get('name', '')}")
            name_item.setData(Qt.UserRole, f["id"])
            name_item.setToolTip("Double click to open folder")
            self.table.setItem(row, 0, name_item)

            id_item = QTableWidgetItem(f.get("id", ""))
            id_item.setForeground(Qt.gray)
            self.table.setItem(row, 1, id_item)

            mtime_item = QTableWidgetItem(format_timestamp(f.get("modifiedTime", "")))
            self.table.setItem(row, 2, mtime_item)

            # Action button: Open
            open_btn = QPushButton("Open")
            open_btn.setProperty("class", "icon-btn")
            open_btn.clicked.connect(lambda _, fid=f["id"], fname=f["name"]: self._navigate_to(fid, fname))
            self.table.setCellWidget(row, 3, open_btn)

    def _filter_folders(self, text: str):
        query = text.strip().lower()
        if not query:
            self._populate_table(self.folders_cache)
            return

        filtered = [f for f in self.folders_cache if query in f.get("name", "").lower()]
        self._populate_table(filtered)

    def _update_breadcrumbs(self):
        """Rebuilds clickable breadcrumb path buttons."""
        # Clear existing
        while self.crumb_layout.count():
            item = self.crumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for idx, (fid, fname) in enumerate(self.breadcrumbs):
            btn = QPushButton(f"📁 {fname}")
            btn.setProperty("class", "crumb-btn")
            btn.clicked.connect(lambda _, target_id=fid, target_idx=idx: self._on_breadcrumb_clicked(target_id, target_idx))
            self.crumb_layout.addWidget(btn)

            if idx < len(self.breadcrumbs) - 1:
                sep = QLabel("/")
                sep.setStyleSheet("color: #64748b; font-weight: bold;")
                self.crumb_layout.addWidget(sep)

        self.crumb_layout.addStretch()

    def _on_breadcrumb_clicked(self, folder_id: str, index: int):
        self.breadcrumbs = self.breadcrumbs[:index + 1]
        self.current_folder_id = folder_id
        self.current_folder_name = self.breadcrumbs[-1][1]
        self.refresh_current_folder()

    def _navigate_to(self, folder_id: str, folder_name: str):
        self.breadcrumbs.append((folder_id, folder_name))
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        self.refresh_current_folder()

    def _navigate_up(self):
        if len(self.breadcrumbs) > 1:
            self.breadcrumbs.pop()
            parent_id, parent_name = self.breadcrumbs[-1]
            self.current_folder_id = parent_id
            self.current_folder_name = parent_name
            self.refresh_current_folder()

    def _on_item_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        name_item = self.table.item(row, 0)
        if name_item:
            folder_id = name_item.data(Qt.UserRole)
            folder_name = name_item.text().replace("📁  ", "").strip()
            self._navigate_to(folder_id, folder_name)

    # ================= CREATE FOLDER (CORE FEATURE) =================

    def _open_new_folder_dialog(self):
        """Opens dialog to create a new folder under current_folder_id."""
        if not self.drive_service.auth_service.is_authenticated():
            QMessageBox.warning(self, "Not Connected", "Please connect to Google Drive first.")
            return

        current_path_str = " / ".join(name for _, name in self.breadcrumbs)
        dialog = NewFolderDialog(parent_folder_name=current_path_str, parent=self)
        if dialog.exec() == NewFolderDialog.Accepted:
            folder_name = dialog.get_folder_name()
            self._create_folder_on_drive(folder_name)

    def _create_folder_on_drive(self, folder_name: str):
        self.status_label.setText(f"Creating folder '{folder_name}' on Google Drive...")
        self.new_folder_btn.setEnabled(False)

        self._create_worker = CreateFolderWorker(
            self.drive_service,
            folder_name,
            self.current_folder_id
        )
        self._create_worker.folder_created.connect(self._on_folder_created_success)
        self._create_worker.create_failed.connect(self._on_folder_created_error)
        self._create_worker.start()

    def _on_folder_created_success(self, folder: Dict[str, Any]):
        self.new_folder_btn.setEnabled(True)
        folder_id = folder.get("id", "")
        folder_name = folder.get("name", "")
        logger.info(f"Folder created: {folder_name} ({folder_id})")

        signal_bus.folder_created.emit(folder_id, folder_name, self.current_folder_id)
        signal_bus.show_notification.emit(
            "Folder Created",
            f"Created folder '{folder_name}' successfully on Google Drive.",
            "success"
        )
        # Automatically refresh folder list
        self.refresh_current_folder()

    def _on_folder_created_error(self, error: str):
        self.new_folder_btn.setEnabled(True)
        logger.error(f"Folder creation error: {error}")
        QMessageBox.critical(self, "Creation Failed", f"Failed to create folder on Google Drive:\n{error}")
        self.status_label.setText("Folder creation failed.")

    # ================= DESTINATION SELECTION =================

    def _select_current_folder_as_destination(self):
        """Sets the currently open folder as the upload destination."""
        path_str = " / ".join(name for _, name in self.breadcrumbs)
        self._active_dest_id = self.current_folder_id
        self._active_dest_path = path_str
        self._update_active_dest_ui()

        # Save to database bookmarks as default
        self.db_manager.add_folder_bookmark(FolderBookmark(
            folder_id=self.current_folder_id,
            folder_name=self.current_folder_name,
            folder_path=path_str,
            is_default=True
        ))

        # Save in settings
        self.db_manager.set_setting("default_destination_id", self.current_folder_id)
        self.db_manager.set_setting("default_destination_path", path_str)

        signal_bus.destination_selected.emit(self.current_folder_id, self.current_folder_name, path_str)
        signal_bus.show_notification.emit(
            "Destination Selected",
            f"Upload destination set to:\n{path_str}\n(ID: {self.current_folder_id})",
            "info"
        )
        logger.info(f"Set push destination: {path_str} ({self.current_folder_id})")

    def get_selected_destination(self) -> tuple[str, str, str]:
        """Returns (folder_id, folder_name, folder_path)."""
        return self._active_dest_id, self.current_folder_name, self._active_dest_path
