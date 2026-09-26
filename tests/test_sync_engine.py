"""
Unit tests for Sync Engine and File Scanner Service.
"""
import os
import tempfile
import time
from pathlib import Path
import pytest

from app.database.models import SyncJobConfig
from app.services.file_service import FileService
from app.services.sync_service import SyncEventHandler
from app.utils.file_checker import is_file_stable
from config.constants import FolderUploadMode


def test_file_scanner_modes():
    with tempfile.TemporaryDirectory() as tmpdir:
        root_dir = Path(tmpdir) / "MyProject"
        sub_dir = root_dir / "docs"
        sub_dir.mkdir(parents=True)

        file1 = root_dir / "main.py"
        file1.write_text("print('hello')")

        file2 = sub_dir / "readme.txt"
        file2.write_text("Documentation")

        # Test Mode 1: CONTENTS_ONLY
        tasks_contents = FileService.scan_folder(str(root_dir), upload_mode=FolderUploadMode.CONTENTS_ONLY)
        assert len(tasks_contents) == 2
        rel_paths_contents = {t.relative_path for t in tasks_contents}
        assert "main.py" in rel_paths_contents
        assert "docs/readme.txt" in rel_paths_contents or "docs\\readme.txt" in rel_paths_contents

        # Test Mode 2: AS_FOLDER
        tasks_as_folder = FileService.scan_folder(str(root_dir), upload_mode=FolderUploadMode.AS_FOLDER)
        assert len(tasks_as_folder) == 2
        rel_paths_folder = {t.relative_path for t in tasks_as_folder}
        assert "MyProject/main.py" in rel_paths_folder
        assert "MyProject/docs/readme.txt" in rel_paths_folder


def test_file_stability_checker():
    with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
        tmp.write(b"Stable binary content")
        tmp_path = tmp.name

    # Stable file should return True quickly
    assert is_file_stable(tmp_path, check_interval=0.2, timeout=1.0) is True


def test_sync_event_handler_debounce():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "data.log"
        test_file.write_text("First write")

        ready_events = []

        def on_ready(job, path, event_type):
            ready_events.append((path, event_type))

        cfg = SyncJobConfig(
            id=1,
            name="Test Sync",
            local_dir=tmpdir,
            drive_folder_id="root",
            drive_folder_path="My Drive",
            sync_modified=True
        )

        handler = SyncEventHandler(
            job_config=cfg,
            on_file_ready=on_ready,
            debounce_seconds=0.3,
            stability_interval=0.1,
            poll_interval=0.1
        )

        # Trigger event
        handler._enqueue_event(str(test_file), "modified")

        # Wait for debounce and stability processing
        time.sleep(1.0)
        handler.stop()

        assert len(ready_events) == 1
        assert ready_events[0][0] == str(test_file)
        assert ready_events[0][1] == "modified"
