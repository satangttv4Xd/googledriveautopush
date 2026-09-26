"""
Unit tests for Upload Engine and Conflict Resolution.
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from app.services.auth_service import AuthService
from app.services.drive_service import DriveService
from app.services.file_service import FileService, FileTask
from config.constants import ConflictPolicy, UploadStatus


@pytest.fixture
def mock_drive_service():
    auth_service = MagicMock(spec=AuthService)
    auth_service.is_authenticated.return_value = True
    auth_service.credentials = MagicMock(valid=True)

    drive_service = DriveService(auth_service)
    drive_service._service = MagicMock()
    return drive_service


def test_conflict_skip(mock_drive_service):
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Hello World")
        tmp_path = tmp.name

    # Mock file existence search returning an existing file
    mock_files = mock_drive_service.service.files()
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {
        "files": [{"id": "existing_id_999", "name": Path(tmp_path).name}]
    }

    status, file_id, final_name = mock_drive_service.upload_file_resumable(
        local_path=tmp_path,
        parent_id="dest_folder_id",
        conflict_policy=ConflictPolicy.SKIP
    )

    assert status == UploadStatus.SKIPPED
    assert file_id == "existing_id_999"


def test_conflict_replace(mock_drive_service):
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"Replacement Content")
        tmp_path = tmp.name

    mock_files = mock_drive_service.service.files()
    mock_files.list.return_value.execute.return_value = {
        "files": [{"id": "existing_id_999", "name": Path(tmp_path).name}]
    }

    # Mock update next_chunk
    mock_update_req = MagicMock()
    mock_update_req.next_chunk.return_value = (None, {"id": "existing_id_999", "name": Path(tmp_path).name})
    mock_files.update.return_value = mock_update_req

    status, file_id, final_name = mock_drive_service.upload_file_resumable(
        local_path=tmp_path,
        parent_id="dest_folder_id",
        conflict_policy=ConflictPolicy.REPLACE
    )

    assert status == UploadStatus.COMPLETED
    assert file_id == "existing_id_999"
    mock_files.update.assert_called_once()


def test_conflict_keep_both_renaming(mock_drive_service):
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp.write(b"Image Content")
        tmp_path = tmp.name

    filename = Path(tmp_path).name
    base = Path(tmp_path).stem

    mock_files = mock_drive_service.service.files()

    # First call: existing file exists -> candidate: base (1).png
    # Second call: candidate base (1).png does not exist
    def mock_list_exec():
        pass

    mock_list = mock_files.list.return_value
    mock_list.execute.side_effect = [
        {"files": [{"id": "existing_id", "name": filename}]},
        {"files": []}  # Candidate 'base (1).png' is available
    ]

    mock_create_req = MagicMock()
    mock_create_req.next_chunk.return_value = (None, {"id": "new_copy_id", "name": f"{base} (1).png"})
    mock_files.create.return_value = mock_create_req

    status, file_id, final_name = mock_drive_service.upload_file_resumable(
        local_path=tmp_path,
        parent_id="dest_folder_id",
        conflict_policy=ConflictPolicy.KEEP_BOTH
    )

    assert status == UploadStatus.COMPLETED
    assert file_id == "new_copy_id"
    assert "(1)" in final_name
