"""
Unit tests for Destination & Folder Manager.
Verifies Google Drive folder creation, multi-level hierarchy generation,
folder browsing, and breadcrumb path resolution using mock Drive API.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.core.exceptions import FolderCreationError
from app.services.auth_service import AuthService
from app.services.drive_service import DriveService
from config.constants import FOLDER_MIME_TYPE


@pytest.fixture
def mock_drive_service():
    auth_service = MagicMock(spec=AuthService)
    auth_service.is_authenticated.return_value = True
    auth_service.credentials = MagicMock(valid=True)

    drive_service = DriveService(auth_service)
    # Mock underlying googleapiclient Resource
    drive_service._service = MagicMock()
    return drive_service


def test_create_folder_success(mock_drive_service):
    mock_files = mock_drive_service.service.files()
    mock_create = mock_files.create.return_value
    mock_create.execute.return_value = {
        "id": "new_folder_123",
        "name": "Project Alpha",
        "parents": ["root"]
    }

    result = mock_drive_service.create_folder(name="Project Alpha", parent_id="root")

    assert result["id"] == "new_folder_123"
    assert result["name"] == "Project Alpha"
    mock_files.create.assert_called_once_with(
        body={
            "name": "Project Alpha",
            "mimeType": FOLDER_MIME_TYPE,
            "parents": ["root"]
        },
        fields="id, name, parents, modifiedTime"
    )


def test_create_folder_empty_name(mock_drive_service):
    with pytest.raises(FolderCreationError):
        mock_drive_service.create_folder(name="   ", parent_id="root")


def test_create_folder_hierarchy_nested(mock_drive_service):
    mock_files = mock_drive_service.service.files()

    # Step 1: list check (returns empty, so folders don't exist yet)
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {"files": []}

    # Step 2: create folder responses
    created_folders = [
        {"id": "id_projects", "name": "Projects", "parents": ["root"]},
        {"id": "id_python", "name": "Python", "parents": ["id_projects"]},
        {"id": "id_backup", "name": "Backup", "parents": ["id_python"]},
    ]
    mock_create = mock_files.create.return_value
    mock_create.execute.side_effect = created_folders

    final_folder = mock_drive_service.create_folder_hierarchy("Projects/Python/Backup", parent_id="root")

    assert final_folder["id"] == "id_backup"
    assert final_folder["name"] == "Backup"
    assert mock_files.create.call_count == 3


def test_list_folders(mock_drive_service):
    mock_files = mock_drive_service.service.files()
    mock_list = mock_files.list.return_value
    mock_list.execute.return_value = {
        "files": [
            {"id": "f1", "name": "Archive", "parents": ["root"]},
            {"id": "f2", "name": "Documents", "parents": ["root"]},
        ],
        "nextPageToken": None
    }

    folders = mock_drive_service.list_folders(parent_id="root")
    assert len(folders) == 2
    assert folders[0]["name"] == "Archive"
    assert folders[1]["name"] == "Documents"


def test_get_folder_breadcrumbs(mock_drive_service):
    mock_files = mock_drive_service.service.files()

    def mock_get_metadata(fileId, **kwargs):
        mock_exec = MagicMock()
        if fileId == "child_id":
            mock_exec.execute.return_value = {"id": "child_id", "name": "Child", "parents": ["parent_id"]}
        elif fileId == "parent_id":
            mock_exec.execute.return_value = {"id": "parent_id", "name": "Parent", "parents": ["root"]}
        return mock_exec

    mock_files.get.side_effect = mock_get_metadata

    crumbs = mock_drive_service.get_folder_breadcrumbs("child_id")
    assert len(crumbs) == 3
    assert crumbs[0] == ("root", "My Drive")
    assert crumbs[1] == ("parent_id", "Parent")
    assert crumbs[2] == ("child_id", "Child")
