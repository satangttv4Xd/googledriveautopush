"""
Google Drive API v3 Service.
Handles folder navigation, folder creation, hierarchy resolution,
duplicate detection, and chunked resumable file uploads with exponential backoff.
"""
import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config.constants import (
    FOLDER_MIME_TYPE,
    INITIAL_BACKOFF,
    MAX_BACKOFF,
    MAX_RETRIES,
    UPLOAD_CHUNK_SIZE,
    ConflictPolicy,
    UploadStatus,
)
from app.core.exceptions import DriveApiError, FolderCreationError, UploadError
from app.services.auth_service import AuthService
from app.utils.logger import logger


class DriveService:
    """High-level Google Drive v3 manager."""

    def __init__(self, auth_service: AuthService):
        self.auth_service = auth_service
        self._service: Optional[Resource] = None
        self._folder_name_cache: Dict[str, str] = {"root": "My Drive"}

    @property
    def service(self) -> Resource:
        """Returns or builds Google Drive Resource."""
        creds = self.auth_service.credentials
        if not creds or not creds.valid:
            raise DriveApiError("Google Drive is not connected or credentials expired.")
        if self._service is None:
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def reset_service(self):
        """Clears cached service instance (e.g. on logout/reconnect)."""
        self._service = None
        self._folder_name_cache = {"root": "My Drive"}

    # ================= FOLDER MANAGEMENT =================

    def list_folders(self, parent_id: str = "root", query_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists child folders inside a parent folder.
        """
        try:
            q = f"mimeType = '{FOLDER_MIME_TYPE}' and '{parent_id}' in parents and trashed = false"
            if query_name:
                escaped = query_name.replace("'", "\\'")
                q += f" and name contains '{escaped}'"

            results = []
            page_token = None
            while True:
                response = self.service.files().list(
                    q=q,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, parents, modifiedTime, shared, owners)",
                    orderBy="name",
                    pageSize=100,
                    pageToken=page_token
                ).execute()

                files = response.get("files", [])
                for f in files:
                    self._folder_name_cache[f["id"]] = f["name"]
                    results.append(f)

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

            return results
        except HttpError as e:
            logger.error(f"Failed to list folders under {parent_id}: {e}")
            raise DriveApiError(f"Error listing folders: {e.reason if hasattr(e, 'reason') else str(e)}")

    def get_folder_metadata(self, folder_id: str) -> Dict[str, Any]:
        """Fetches folder details by ID."""
        if folder_id == "root":
            return {"id": "root", "name": "My Drive", "parents": []}

        try:
            folder = self.service.files().get(
                fileId=folder_id,
                fields="id, name, parents, modifiedTime"
            ).execute()
            self._folder_name_cache[folder["id"]] = folder["name"]
            return folder
        except HttpError as e:
            logger.error(f"Failed to get folder metadata for {folder_id}: {e}")
            raise DriveApiError(f"Could not retrieve folder {folder_id}: {e.reason if hasattr(e, 'reason') else str(e)}")

    def get_folder_name(self, folder_id: str) -> str:
        """Retrieves folder name with cache fallback."""
        if folder_id == "root":
            return "My Drive"
        if folder_id in self._folder_name_cache:
            return self._folder_name_cache[folder_id]
        try:
            meta = self.get_folder_metadata(folder_id)
            return meta.get("name", folder_id)
        except Exception:
            return folder_id

    def get_folder_breadcrumbs(self, folder_id: str) -> List[Tuple[str, str]]:
        """
        Traverses hierarchy upwards to construct breadcrumb trail:
        [('root', 'My Drive'), ('f1', 'Folder A'), ..., ('current_id', 'Current')]
        """
        if folder_id == "root":
            return [("root", "My Drive")]

        trail = []
        curr_id = folder_id

        # Limit depth to prevent infinite loops in shared drive edge-cases
        max_depth = 20
        visited = set()

        while curr_id and curr_id != "root" and max_depth > 0:
            if curr_id in visited:
                break
            visited.add(curr_id)

            try:
                meta = self.get_folder_metadata(curr_id)
                name = meta.get("name", "Unknown Folder")
                trail.append((curr_id, name))
                parents = meta.get("parents", [])
                curr_id = parents[0] if parents else None
                max_depth -= 1
            except Exception as e:
                logger.warning(f"Error resolving parent for {curr_id}: {e}")
                break

        trail.append(("root", "My Drive"))
        trail.reverse()
        return trail

    def get_breadcrumb_path_string(self, folder_id: str) -> str:
        """Returns formatted string like 'My Drive / Projects / Python'."""
        crumbs = self.get_folder_breadcrumbs(folder_id)
        return " / ".join(name for _, name in crumbs)

    def create_folder(self, name: str, parent_id: str = "root") -> Dict[str, Any]:
        """
        Creates a new folder on Google Drive.
        """
        cleaned_name = name.strip()
        if not cleaned_name:
            raise FolderCreationError("Folder name cannot be empty.")

        body = {
            "name": cleaned_name,
            "mimeType": FOLDER_MIME_TYPE,
            "parents": [parent_id]
        }

        try:
            logger.info(f"Creating folder '{cleaned_name}' under parent ID '{parent_id}'...")
            folder = self.service.files().create(
                body=body,
                fields="id, name, parents, modifiedTime"
            ).execute()

            self._folder_name_cache[folder["id"]] = folder["name"]
            logger.info(f"Folder '{cleaned_name}' created successfully with ID: {folder['id']}")
            return folder
        except HttpError as e:
            logger.error(f"Failed to create folder '{cleaned_name}': {e}")
            raise FolderCreationError(f"Failed to create folder: {e.reason if hasattr(e, 'reason') else str(e)}")

    def create_folder_hierarchy(self, path_str: str, parent_id: str = "root") -> Dict[str, Any]:
        """
        Creates nested folder structure (e.g. 'Projects/Python/App1/Backup').
        Finds existing folders along the path or creates missing ones.
        """
        parts = [p.strip() for p in path_str.replace("\\", "/").split("/") if p.strip()]
        if not parts:
            return self.get_folder_metadata(parent_id)

        curr_parent = parent_id
        last_folder = None

        for part in parts:
            # Check if folder already exists in curr_parent
            escaped = part.replace("'", "\\'")
            q = f"mimeType = '{FOLDER_MIME_TYPE}' and '{curr_parent}' in parents and name = '{escaped}' and trashed = false"
            res = self.service.files().list(q=q, fields="files(id, name, parents)", pageSize=1).execute()
            files = res.get("files", [])

            if files:
                last_folder = files[0]
                curr_parent = last_folder["id"]
                self._folder_name_cache[curr_parent] = last_folder["name"]
            else:
                last_folder = self.create_folder(name=part, parent_id=curr_parent)
                curr_parent = last_folder["id"]

        return last_folder or self.get_folder_metadata(parent_id)

    # ================= FILE OPERATIONS & UPLOAD =================

    def find_file_in_folder(self, filename: str, parent_id: str) -> Optional[Dict[str, Any]]:
        """Checks if a file with the given name exists in the parent folder."""
        try:
            escaped = filename.replace("'", "\\'")
            q = f"'{parent_id}' in parents and name = '{escaped}' and trashed = false and mimeType != '{FOLDER_MIME_TYPE}'"
            response = self.service.files().list(
                q=q,
                fields="files(id, name, size, modifiedTime)",
                pageSize=1
            ).execute()
            files = response.get("files", [])
            return files[0] if files else None
        except Exception as e:
            logger.warning(f"Error checking file existence for {filename}: {e}")
            return None

    def upload_file_resumable(
        self,
        local_path: str,
        parent_id: str = "root",
        target_name: Optional[str] = None,
        conflict_policy: str = ConflictPolicy.KEEP_BOTH,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
        is_paused: Optional[Callable[[], bool]] = None,
    ) -> Tuple[str, str, Optional[str]]:
        """
        Uploads a local file to Google Drive using resumable chunked upload.
        Handles conflict policies (SKIP, REPLACE, KEEP_BOTH).
        
        Returns:
            Tuple[status, drive_file_id, final_filename]
        """
        path = Path(local_path)
        if not path.is_file():
            raise UploadError(f"Local file does not exist: {local_path}")

        file_size = path.stat().st_size
        filename = target_name or path.name

        # 1. Conflict Check
        existing = self.find_file_in_folder(filename, parent_id)
        existing_id = None

        if existing:
            if conflict_policy == ConflictPolicy.SKIP:
                logger.info(f"File '{filename}' already exists in destination. Skipping (Policy: SKIP).")
                return UploadStatus.SKIPPED, existing["id"], filename
            elif conflict_policy == ConflictPolicy.REPLACE:
                logger.info(f"File '{filename}' exists. Updating media (Policy: REPLACE).")
                existing_id = existing["id"]
            elif conflict_policy == ConflictPolicy.KEEP_BOTH:
                # Generate unique name: 'example (1).png'
                base, ext = os.path.splitext(filename)
                counter = 1
                while True:
                    candidate = f"{base} ({counter}){ext}"
                    if not self.find_file_in_folder(candidate, parent_id):
                        filename = candidate
                        break
                    counter += 1
                logger.info(f"File conflict resolved. Renamed to '{filename}' (Policy: KEEP_BOTH).")

        # 2. Determine MIME type
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"

        media = MediaFileUpload(
            str(path),
            mimetype=mime_type,
            chunksize=UPLOAD_CHUNK_SIZE,
            resumable=True
        )

        # 3. Create or Update API Request
        if existing_id:
            # Replace existing file
            request = self.service.files().update(
                fileId=existing_id,
                media_body=media,
                fields="id, name, size"
            )
        else:
            # Create new file
            body = {
                "name": filename,
                "parents": [parent_id]
            }
            request = self.service.files().create(
                body=body,
                media_body=media,
                fields="id, name, size"
            )

        # 4. Execute Resumable Chunks with Exponential Backoff
        response = None
        last_progress_bytes = 0

        while response is None:
            # Cancellation Check
            if is_cancelled and is_cancelled():
                logger.info(f"Upload of {filename} cancelled by user.")
                return UploadStatus.CANCELLED, "", filename

            # Pause Check
            while is_paused and is_paused():
                if is_cancelled and is_cancelled():
                    return UploadStatus.CANCELLED, "", filename
                time.sleep(0.5)

            # Attempt chunk transfer with retry logic
            backoff = INITIAL_BACKOFF
            retry_count = 0

            while retry_count <= MAX_RETRIES:
                try:
                    status, response = request.next_chunk()
                    if status:
                        uploaded_bytes = status.resumable_progress
                        last_progress_bytes = uploaded_bytes
                        if progress_callback:
                            progress_callback(uploaded_bytes, file_size)
                    break
                except HttpError as err:
                    if err.resp.status in [500, 502, 503, 504, 429]:
                        retry_count += 1
                        if retry_count > MAX_RETRIES:
                            raise UploadError(f"Max retries exceeded for {filename}: {err}")
                        logger.warning(f"HTTP {err.resp.status} encountered. Retrying chunk in {backoff:.1f}s...")
                        time.sleep(backoff)
                        backoff = min(backoff * 2, MAX_BACKOFF)
                    else:
                        raise UploadError(f"HTTP error during upload of {filename}: {err}")
                except Exception as ex:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        raise UploadError(f"Network error during upload of {filename}: {ex}")
                    logger.warning(f"Network error: {ex}. Retrying chunk in {backoff:.1f}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)

        # If 0-byte file, progress callback might not have reached 100%
        if progress_callback and file_size == 0:
            progress_callback(0, 0)

        drive_file_id = response.get("id") if response else (existing_id or "")
        logger.info(f"Upload finished for '{filename}'. Drive File ID: {drive_file_id}")
        return UploadStatus.COMPLETED, drive_file_id, filename
