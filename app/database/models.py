"""
Database entity data models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from config.constants import UploadStatus


@dataclass
class UploadQueueItem:
    id: Optional[int] = None
    local_path: str = ""
    drive_folder_id: str = "root"
    relative_path: str = ""
    file_size: int = 0
    status: str = UploadStatus.WAITING
    error_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class UploadHistoryItem:
    id: Optional[int] = None
    filename: str = ""
    local_path: str = ""
    drive_file_id: Optional[str] = None
    drive_folder_id: str = "root"
    drive_folder_path: str = "My Drive"
    file_size: int = 0
    status: str = UploadStatus.COMPLETED
    error_message: Optional[str] = None
    upload_speed: float = 0.0
    duration_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SyncJobConfig:
    id: Optional[int] = None
    name: str = ""
    local_dir: str = ""
    drive_folder_id: str = "root"
    drive_folder_path: str = "My Drive"
    sync_modified: bool = True
    is_active: bool = True
    last_synced: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FolderBookmark:
    id: Optional[int] = None
    folder_id: str = "root"
    folder_name: str = "My Drive"
    folder_path: str = "My Drive"
    is_default: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
