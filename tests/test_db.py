"""
Unit tests for DatabaseManager and SQLite storage.
"""
import os
import tempfile
from pathlib import Path
import pytest

from app.database.db_manager import DatabaseManager
from app.database.models import (
    FolderBookmark,
    SyncJobConfig,
    UploadHistoryItem,
    UploadQueueItem,
)
from config.constants import UploadStatus


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_autopush.db"
        manager = DatabaseManager(db_path=db_path)
        try:
            yield manager
        finally:
            manager.close()


def test_init_db(temp_db):
    bookmarks = temp_db.get_folder_bookmarks()
    assert len(bookmarks) >= 1
    assert bookmarks[0].folder_id == "root"
    assert bookmarks[0].is_default is True


def test_history_crud(temp_db):
    item = UploadHistoryItem(
        filename="report.pdf",
        local_path="D:/Docs/report.pdf",
        drive_file_id="drive123",
        drive_folder_id="root",
        drive_folder_path="My Drive",
        file_size=1048576,
        status=UploadStatus.COMPLETED,
        upload_speed=524288.0,
        duration_seconds=2.0
    )
    rec_id = temp_db.add_history_record(item)
    assert rec_id > 0

    history = temp_db.get_history()
    assert len(history) == 1
    assert history[0].filename == "report.pdf"
    assert history[0].drive_file_id == "drive123"

    stats = temp_db.get_history_stats()
    assert stats["total_count"] == 1
    assert stats["completed_count"] == 1
    assert stats["total_bytes"] == 1048576

    temp_db.clear_history()
    assert len(temp_db.get_history()) == 0


def test_queue_crud(temp_db):
    items = [
        UploadQueueItem(
            local_path="D:/Photos/cat.jpg",
            drive_folder_id="folder_photos",
            relative_path="cat.jpg",
            file_size=500000,
            status=UploadStatus.WAITING
        ),
        UploadQueueItem(
            local_path="D:/Photos/dog.jpg",
            drive_folder_id="folder_photos",
            relative_path="dog.jpg",
            file_size=600000,
            status=UploadStatus.WAITING
        )
    ]
    temp_db.add_queue_items(items)
    pending = temp_db.get_pending_queue()
    assert len(pending) == 2

    # Update status
    temp_db.update_queue_item_status(pending[0].id, UploadStatus.COMPLETED)
    assert len(temp_db.get_pending_queue()) == 1

    temp_db.remove_queue_item(pending[1].id)
    assert len(temp_db.get_pending_queue()) == 0


def test_sync_configs_crud(temp_db):
    config = SyncJobConfig(
        name="Backup Python",
        local_dir="D:/Python",
        drive_folder_id="drive_py_folder",
        drive_folder_path="My Drive / Backup",
        sync_modified=True,
        is_active=True
    )
    job_id = temp_db.add_sync_config(config)
    assert job_id > 0

    jobs = temp_db.get_sync_configs()
    assert len(jobs) == 1
    assert jobs[0].name == "Backup Python"
    assert jobs[0].is_active is True

    # Pause job
    temp_db.update_sync_status(job_id, is_active=False)
    jobs = temp_db.get_sync_configs()
    assert jobs[0].is_active is False

    temp_db.delete_sync_config(job_id)
    assert len(temp_db.get_sync_configs()) == 0


def test_settings_storage(temp_db):
    temp_db.set_setting("theme", "dark")
    temp_db.set_setting("chunk_size_mb", "10")

    assert temp_db.get_setting("theme") == "dark"
    assert temp_db.get_setting("chunk_size_mb") == "10"
    assert temp_db.get_setting("non_existent", "default_val") == "default_val"
