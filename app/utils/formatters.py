"""
Formatting utilities for file sizes, transfer speeds, durations, and timestamps.
"""
from datetime import datetime
import os
from typing import Union


def format_bytes(bytes_count: Union[int, float]) -> str:
    """Format bytes count into human-readable string (KB, MB, GB)."""
    if bytes_count is None or bytes_count < 0:
        return "0 B"
    
    bytes_float = float(bytes_count)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while bytes_float >= 1024.0 and i < len(units) - 1:
        bytes_float /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(bytes_float)} {units[i]}"
    return f"{bytes_float:.2f} {units[i]}"


def format_speed(bytes_per_sec: float) -> str:
    """Format transfer speed into human-readable rate."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "0 KB/s"
    return f"{format_bytes(bytes_per_sec)}/s"


def format_eta(seconds: float) -> str:
    """Format remaining seconds into human-readable ETA (HH:MM:SS or MM:SS)."""
    if seconds is None or seconds < 0 or seconds > 86400 * 7:
        return "--:--"
    
    sec = int(seconds)
    hours, remainder = divmod(sec, 3600)
    minutes, seconds_left = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds_left:02d}"
    return f"{minutes:02d}:{seconds_left:02d}"


def format_timestamp(ts: Union[str, float, datetime] = None) -> str:
    """Format timestamp into readable date time."""
    if ts is None:
        now = datetime.now()
    elif isinstance(ts, (int, float)):
        now = datetime.fromtimestamp(ts)
    elif isinstance(ts, str):
        try:
            now = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return ts
    elif isinstance(ts, datetime):
        now = ts
    else:
        return str(ts)
    
    return now.strftime("%Y-%m-%d %H:%M:%S")


def get_file_extension(filename: str) -> str:
    """Extract upper-case file extension without dot."""
    ext = os.path.splitext(filename)[1]
    if ext:
        return ext[1:].upper()
    return "FILE"
