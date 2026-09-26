"""
Settings configuration manager.
Handles loading and saving application preferences in SQLite.
"""
from typing import Any, Dict
from config.constants import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_TOKEN_PATH,
    ConflictPolicy,
)


class AppSettings:
    """Manages application-wide runtime and persistent settings."""

    DEFAULTS = {
        "credentials_path": str(DEFAULT_CREDENTIALS_PATH),
        "token_path": str(DEFAULT_TOKEN_PATH),
        "default_destination_id": "root",
        "default_destination_path": "My Drive",
        "conflict_policy": ConflictPolicy.KEEP_BOTH,
        "auto_sync_enabled": "false",
        "sync_debounce_seconds": "5",
        "sync_modified_files": "true",
        "theme": "dark",
        "chunk_size_mb": "5",
        "notify_on_complete": "true",
    }

    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self._memory_cache: Dict[str, str] = dict(self.DEFAULTS)
        if self.db_manager:
            self.load_from_db()

    def load_from_db(self):
        """Loads all settings from database into memory cache."""
        if not self.db_manager:
            return
        saved = self.db_manager.get_all_settings()
        self._memory_cache.update(saved)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a setting value."""
        return self._memory_cache.get(key, default if default is not None else self.DEFAULTS.get(key))

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Retrieves boolean setting."""
        val = str(self.get(key, str(default))).lower()
        return val in ("true", "1", "yes", "on")

    def get_int(self, key: str, default: int = 0) -> int:
        """Retrieves integer setting."""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Saves a setting to memory cache and database."""
        val_str = str(value)
        self._memory_cache[key] = val_str
        if self.db_manager:
            self.db_manager.set_setting(key, val_str)
