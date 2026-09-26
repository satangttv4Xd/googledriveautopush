"""
Local File System and Hierarchy Scanner Service.
Prepares file batches and preserves relative directory structures.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from config.constants import FolderUploadMode
from app.utils.formatters import get_file_extension
from app.utils.logger import logger


@dataclass
class FileTask:
    """Represents a single local file queued for upload."""
    local_path: str
    relative_path: str  # e.g. "subfolder/image.png" or "image.png"
    filename: str
    file_size: int
    file_type: str


class FileService:
    """Utilities for selecting, scanning, and structuring local files for upload."""

    @staticmethod
    def get_file_task(local_file_path: str, relative_path: Optional[str] = None) -> Optional[FileTask]:
        """Creates a FileTask from a single file path."""
        path = Path(local_file_path)
        if not path.is_file():
            return None
        try:
            stat = path.stat()
            return FileTask(
                local_path=str(path.resolve()),
                relative_path=relative_path or path.name,
                filename=path.name,
                file_size=stat.st_size,
                file_type=get_file_extension(path.name)
            )
        except Exception as e:
            logger.warning(f"Could not read file {local_file_path}: {e}")
            return None

    @staticmethod
    def scan_folder(
        folder_path: str,
        upload_mode: str = FolderUploadMode.CONTENTS_ONLY
    ) -> List[FileTask]:
        """
        Recursively scans a local folder and returns a list of FileTask objects.
        
        If upload_mode == AS_FOLDER:
            relative paths start with folder_name / ...
        If upload_mode == CONTENTS_ONLY:
            relative paths are relative to inside the folder
        """
        root_path = Path(folder_path).resolve()
        if not root_path.is_dir():
            return []

        folder_name = root_path.name
        tasks: List[FileTask] = []

        for dirpath, _, filenames in os.walk(root_path):
            dir_p = Path(dirpath)
            for fname in filenames:
                full_path = dir_p / fname
                try:
                    rel_to_root = full_path.relative_to(root_path)
                    if upload_mode == FolderUploadMode.AS_FOLDER:
                        rel_path_str = f"{folder_name}/{rel_to_root.as_posix()}"
                    else:
                        rel_path_str = rel_to_root.as_posix()

                    stat = full_path.stat()
                    tasks.append(FileTask(
                        local_path=str(full_path),
                        relative_path=rel_path_str,
                        filename=fname,
                        file_size=stat.st_size,
                        file_type=get_file_extension(fname)
                    ))
                except Exception as e:
                    logger.warning(f"Skipping inaccessible file {full_path}: {e}")

        return tasks

    @staticmethod
    def calculate_totals(tasks: List[FileTask]) -> Tuple[int, int]:
        """Calculates (total_files_count, total_bytes_size)."""
        total_files = len(tasks)
        total_bytes = sum(t.file_size for t in tasks)
        return total_files, total_bytes
