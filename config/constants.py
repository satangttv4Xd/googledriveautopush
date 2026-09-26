"""
Application Constants and Defaults for Google Drive AutoPush.
"""
from pathlib import Path
import sys

APP_NAME = "Google Drive AutoPush"
APP_VERSION = "1.0.0"
APP_ORG = "AutoPush"

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# User Data & Storage Paths
USER_DATA_DIR = BASE_DIR / "data"
USER_DATA_DIR.mkdir(exist_ok=True)

DEFAULT_CREDENTIALS_PATH = BASE_DIR / "credentials.json"
DEFAULT_TOKEN_PATH = USER_DATA_DIR / "token.json"
DEFAULT_DB_PATH = USER_DATA_DIR / "autopush.db"
DEFAULT_LOG_PATH = USER_DATA_DIR / "autopush.log"

# Google Drive API Scopes
# Using drive full scope allows managing folders in My Drive and creating new folders easily
DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Google Drive MIME Types
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"

# Conflict Policies
class ConflictPolicy:
    SKIP = "skip"
    REPLACE = "replace"
    KEEP_BOTH = "keep_both"

    CHOICES = [
        (SKIP, "ข้ามไฟล์ (Skip)"),
        (REPLACE, "เขียนทับไฟล์เดิม (Replace)"),
        (KEEP_BOTH, "เก็บไว้ทั้งคู่ (Keep Both - เปลี่ยนชื่อใหม่)"),
    ]

# Upload Modes for Folders
class FolderUploadMode:
    CONTENTS_ONLY = "contents"      # Upload files and subfolders into destination
    AS_FOLDER = "as_folder"         # Create root folder first, then upload contents

# Upload Statuses
class UploadStatus:
    WAITING = "waiting"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    PAUSED = "paused"

# Upload Chunk Size for Resumable Upload (5 MB)
UPLOAD_CHUNK_SIZE = 5 * 1024 * 1024

# Retry settings
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 32.0     # seconds

# Watchdog sync debounce
DEFAULT_SYNC_DEBOUNCE_SECONDS = 5.0
DEFAULT_STABILITY_CHECK_INTERVAL = 1.0
