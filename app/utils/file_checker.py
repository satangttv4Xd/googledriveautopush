"""
File stability and integrity checker.
Ensures files are fully written and closed before upload or sync processing.
"""
import os
import time
from pathlib import Path
from typing import Optional, Tuple
from app.utils.logger import logger


def is_file_stable(file_path: str, check_interval: float = 0.8, timeout: float = 5.0) -> bool:
    """
    Checks if a local file is finished being written and is not currently locked.
    
    1. Tests if the file can be opened for reading.
    2. Verifies that file size remains unchanged over check_interval.
    """
    path = Path(file_path)
    if not path.is_file():
        return False

    start_time = time.time()
    
    while time.time() - start_time <= timeout:
        # Check 1: Can we open the file for reading?
        try:
            with open(path, "rb") as f:
                # Seek to end to ensure file size can be read
                f.seek(0, os.SEEK_END)
        except (PermissionError, IOError, OSError) as e:
            # File is locked by another process (e.g. copying, downloading)
            logger.debug(f"File locked or inaccessible: {path} ({e})")
            time.sleep(0.3)
            continue

        # Check 2: Size stability
        try:
            size1 = path.stat().st_size
            mtime1 = path.stat().st_mtime
            time.sleep(check_interval)
            size2 = path.stat().st_size
            mtime2 = path.stat().st_mtime

            if size1 == size2 and mtime1 == mtime2:
                # Size and mtime are stable
                return True
            else:
                logger.debug(f"File {path} is still changing (size: {size1} -> {size2})")
        except (FileNotFoundError, PermissionError):
            time.sleep(0.3)

    return False


def get_file_metadata(file_path: str) -> Optional[dict]:
    """Retrieves file size, modification time, and existence."""
    path = Path(file_path)
    if not path.exists():
        return None
    try:
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path.resolve()),
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "is_dir": path.is_dir(),
        }
    except Exception as e:
        logger.error(f"Error reading file stat for {file_path}: {e}")
        return None
