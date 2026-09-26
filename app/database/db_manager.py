"""
SQLite Database Manager for Google Drive AutoPush.
Handles persistent storage for upload history, queues, sync jobs, folder bookmarks, and app settings.
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.database.models import (
    FolderBookmark,
    SyncJobConfig,
    UploadHistoryItem,
    UploadQueueItem,
)
from app.utils.logger import logger
from config.constants import DEFAULT_DB_PATH, UploadStatus


class DatabaseManager:
    """Thread-safe SQLite manager with connection pooling / lock."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def close(self):
        """Forces WAL checkpoint and clean release of database locks."""
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.close()
        except Exception:
            pass

    def _init_db(self):
        """Creates necessary database tables and indices."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()

            # Upload History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    drive_file_id TEXT,
                    drive_folder_id TEXT NOT NULL,
                    drive_folder_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    upload_speed REAL DEFAULT 0.0,
                    duration_seconds REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL
                );
            """)

            # Upload Queue Table (for persistence and recovery)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS upload_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_path TEXT NOT NULL,
                    drive_folder_id TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Sync Configuration Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    local_dir TEXT NOT NULL,
                    drive_folder_id TEXT NOT NULL,
                    drive_folder_path TEXT NOT NULL,
                    sync_modified INTEGER NOT NULL DEFAULT 1,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    last_synced TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Folder Bookmarks / Destinations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS folder_bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    folder_id TEXT NOT NULL UNIQUE,
                    folder_name TEXT NOT NULL,
                    folder_path TEXT NOT NULL,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
            """)

            # App Settings Table (Key-Value)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            # Indices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON upload_history(timestamp DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_status ON upload_history(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON upload_queue(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_active ON sync_configs(is_active);")

            # Seed default destination bookmark if none exists
            cursor.execute("SELECT COUNT(*) FROM folder_bookmarks;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT OR IGNORE INTO folder_bookmarks (folder_id, folder_name, folder_path, is_default, created_at)
                    VALUES ('root', 'My Drive', 'My Drive', 1, datetime('now'));
                """)

            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")

    # ================= HISTORY OPERATIONS =================

    def add_history_record(self, item: UploadHistoryItem) -> int:
        """Adds a completed or failed upload to history."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO upload_history (
                    filename, local_path, drive_file_id, drive_folder_id, drive_folder_path,
                    file_size, status, error_message, upload_speed, duration_seconds, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.filename, item.local_path, item.drive_file_id, item.drive_folder_id,
                item.drive_folder_path, item.file_size, item.status, item.error_message,
                item.upload_speed, item.duration_seconds, item.timestamp
            ))
            conn.commit()
            return cursor.lastrowid

    def get_history(
        self,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[UploadHistoryItem]:
        """Queries upload history with optional search and status filter."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM upload_history WHERE 1=1"
            params: List[Any] = []

            if search_query:
                query += " AND (filename LIKE ? OR drive_folder_path LIKE ?)"
                params.extend([f"%{search_query}%", f"%{search_query}%"])

            if status_filter and status_filter.lower() != "all":
                query += " AND status = ?"
                params.append(status_filter.lower())

            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                UploadHistoryItem(
                    id=row["id"],
                    filename=row["filename"],
                    local_path=row["local_path"],
                    drive_file_id=row["drive_file_id"],
                    drive_folder_id=row["drive_folder_id"],
                    drive_folder_path=row["drive_folder_path"],
                    file_size=row["file_size"],
                    status=row["status"],
                    error_message=row["error_message"],
                    upload_speed=row["upload_speed"],
                    duration_seconds=row["duration_seconds"],
                    timestamp=row["timestamp"]
                )
                for row in rows
            ]

    def get_history_stats(self) -> Dict[str, Any]:
        """Calculates aggregate metrics for history dashboard."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_count,
                    COALESCE(SUM(file_size), 0) as total_bytes,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END), 0) as completed_count,
                    COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed_count,
                    COALESCE(SUM(CASE WHEN status = 'skipped' THEN 1 ELSE 0 END), 0) as skipped_count
                FROM upload_history
            """)
            row = cursor.fetchone()
            return dict(row) if row else {
                "total_count": 0, "total_bytes": 0,
                "completed_count": 0, "failed_count": 0, "skipped_count": 0
            }

    def clear_history(self):
        """Clears all records from history."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM upload_history")
            conn.commit()

    # ================= QUEUE OPERATIONS =================

    def add_queue_items(self, items: List[UploadQueueItem]):
        """Adds a batch of items to the persistent upload queue."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO upload_queue (
                    local_path, drive_folder_id, relative_path, file_size, status, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (item.local_path, item.drive_folder_id, item.relative_path, item.file_size,
                 item.status, item.error_message, item.created_at)
                for item in items
            ])
            conn.commit()

    def get_pending_queue(self) -> List[UploadQueueItem]:
        """Retrieves waiting or paused queue items to resume."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM upload_queue 
                WHERE status IN ('waiting', 'uploading', 'paused') 
                ORDER BY id ASC
            """)
            return [
                UploadQueueItem(
                    id=row["id"],
                    local_path=row["local_path"],
                    drive_folder_id=row["drive_folder_id"],
                    relative_path=row["relative_path"],
                    file_size=row["file_size"],
                    status=row["status"],
                    error_message=row["error_message"],
                    created_at=row["created_at"]
                )
                for row in cursor.fetchall()
            ]

    def update_queue_item_status(self, item_id: int, status: str, error_message: Optional[str] = None):
        """Updates queue item status."""
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                UPDATE upload_queue 
                SET status = ?, error_message = ? 
                WHERE id = ?
            """, (status, error_message, item_id))
            conn.commit()

    def remove_queue_item(self, item_id: int):
        """Removes an item from queue."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM upload_queue WHERE id = ?", (item_id,))
            conn.commit()

    def clear_queue(self):
        """Removes all items from the queue."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM upload_queue")
            conn.commit()

    # ================= SYNC CONFIGS OPERATIONS =================

    def get_sync_configs(self) -> List[SyncJobConfig]:
        """Retrieves all sync configurations."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sync_configs ORDER BY id ASC")
            return [
                SyncJobConfig(
                    id=row["id"],
                    name=row["name"],
                    local_dir=row["local_dir"],
                    drive_folder_id=row["drive_folder_id"],
                    drive_folder_path=row["drive_folder_path"],
                    sync_modified=bool(row["sync_modified"]),
                    is_active=bool(row["is_active"]),
                    last_synced=row["last_synced"],
                    created_at=row["created_at"]
                )
                for row in cursor.fetchall()
            ]

    def add_sync_config(self, config: SyncJobConfig) -> int:
        """Adds a new sync job configuration."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_configs (
                    name, local_dir, drive_folder_id, drive_folder_path, sync_modified, is_active, last_synced, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                config.name, config.local_dir, config.drive_folder_id, config.drive_folder_path,
                1 if config.sync_modified else 0, 1 if config.is_active else 0,
                config.last_synced, config.created_at
            ))
            conn.commit()
            return cursor.lastrowid

    def update_sync_config(self, config: SyncJobConfig):
        """Updates an existing sync job configuration."""
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                UPDATE sync_configs SET
                    name = ?, local_dir = ?, drive_folder_id = ?, drive_folder_path = ?,
                    sync_modified = ?, is_active = ?, last_synced = ?
                WHERE id = ?
            """, (
                config.name, config.local_dir, config.drive_folder_id, config.drive_folder_path,
                1 if config.sync_modified else 0, 1 if config.is_active else 0,
                config.last_synced, config.id
            ))
            conn.commit()

    def update_sync_status(self, job_id: int, is_active: bool):
        """Enables or disables a sync job."""
        with self._lock, self._get_connection() as conn:
            conn.execute("UPDATE sync_configs SET is_active = ? WHERE id = ?", (1 if is_active else 0, job_id))
            conn.commit()

    def update_sync_last_run(self, job_id: int, timestamp: str):
        """Updates last_synced timestamp."""
        with self._lock, self._get_connection() as conn:
            conn.execute("UPDATE sync_configs SET last_synced = ? WHERE id = ?", (timestamp, job_id))
            conn.commit()

    def delete_sync_config(self, job_id: int):
        """Deletes a sync job configuration."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM sync_configs WHERE id = ?", (job_id,))
            conn.commit()

    # ================= FOLDER BOOKMARKS OPERATIONS =================

    def get_folder_bookmarks(self) -> List[FolderBookmark]:
        """Retrieves all bookmarked or remembered destination folders."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM folder_bookmarks ORDER BY is_default DESC, id DESC")
            return [
                FolderBookmark(
                    id=row["id"],
                    folder_id=row["folder_id"],
                    folder_name=row["folder_name"],
                    folder_path=row["folder_path"],
                    is_default=bool(row["is_default"]),
                    created_at=row["created_at"]
                )
                for row in cursor.fetchall()
            ]

    def add_folder_bookmark(self, bookmark: FolderBookmark):
        """Saves a destination folder bookmark."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            if bookmark.is_default:
                cursor.execute("UPDATE folder_bookmarks SET is_default = 0")
            cursor.execute("""
                INSERT OR REPLACE INTO folder_bookmarks (folder_id, folder_name, folder_path, is_default, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (bookmark.folder_id, bookmark.folder_name, bookmark.folder_path, 1 if bookmark.is_default else 0, bookmark.created_at))
            conn.commit()

    def set_default_folder_bookmark(self, folder_id: str):
        """Sets a bookmark as default."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE folder_bookmarks SET is_default = 0")
            cursor.execute("UPDATE folder_bookmarks SET is_default = 1 WHERE folder_id = ?", (folder_id,))
            conn.commit()

    def delete_folder_bookmark(self, folder_id: str):
        """Deletes a folder bookmark (cannot delete root)."""
        if folder_id == "root":
            return
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM folder_bookmarks WHERE folder_id = ?", (folder_id,))
            conn.commit()

    # ================= SETTINGS (KEY-VALUE) =================

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a single setting value."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        """Stores a setting value."""
        with self._lock, self._get_connection() as conn:
            conn.execute("""
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        """Retrieves all settings as a key-value dictionary."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
