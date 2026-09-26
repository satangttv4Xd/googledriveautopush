"""
Core custom exceptions for Google Drive AutoPush.
"""


class AutoPushError(Exception):
    """Base exception for AutoPush."""
    pass


class AuthError(AutoPushError):
    """Raised when authentication fails or credentials are invalid."""
    pass


class DriveApiError(AutoPushError):
    """Raised when Google Drive API operations fail."""
    pass


class FolderCreationError(DriveApiError):
    """Raised when creating a folder in Google Drive fails."""
    pass


class UploadError(AutoPushError):
    """Raised when file upload fails."""
    pass


class SyncError(AutoPushError):
    """Raised when sync engine operations fail."""
    pass
