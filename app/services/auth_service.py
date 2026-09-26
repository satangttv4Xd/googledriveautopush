"""
Google Drive OAuth 2.0 Desktop Authentication Service.
Handles token lifecycle, secure storage, automatic token refreshing, and account information retrieval.
"""
from pathlib import Path
import json
import os
from typing import Any, Dict, Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.constants import (
    DEFAULT_CREDENTIALS_PATH,
    DEFAULT_TOKEN_PATH,
    DRIVE_SCOPES,
)
from app.core.exceptions import AuthError
from app.utils.logger import logger


class AuthService:
    """Manages Google OAuth 2.0 authentication lifecycle."""

    def __init__(
        self,
        credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
        token_path: Path = DEFAULT_TOKEN_PATH,
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._credentials: Optional[Credentials] = None
        self._user_profile: Dict[str, Any] = {}

    @property
    def credentials(self) -> Optional[Credentials]:
        """Returns active credentials, attempting refresh if expired."""
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                logger.info("Credentials expired. Attempting automatic refresh...")
                self._credentials.refresh(Request())
                self._save_token(self._credentials)
                logger.info("Credentials refreshed successfully.")
            except Exception as e:
                logger.error(f"Failed to auto-refresh credentials: {e}")
                self._credentials = None
        return self._credentials

    def is_authenticated(self) -> bool:
        """Checks if valid credentials exist."""
        creds = self.credentials
        return creds is not None and creds.valid

    def initialize_session(self) -> bool:
        """
        Attempts to restore a previous session from token.json.
        Returns True if authenticated, False otherwise.
        """
        if not self.token_path.exists():
            logger.info("No saved token found.")
            return False

        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), DRIVE_SCOPES)
            if creds and creds.expired and creds.refresh_token:
                logger.info("Stored token expired. Refreshing...")
                creds.refresh(Request())
                self._save_token(creds)

            if creds and creds.valid:
                self._credentials = creds
                logger.info("Restored authentication session successfully.")
                self.fetch_account_info()
                return True
            else:
                logger.warning("Stored token is invalid.")
                return False
        except Exception as e:
            logger.warning(f"Error loading stored token: {e}")
            return False

    def login(self, client_secrets_file: Optional[Path] = None, port: int = 0) -> Tuple[bool, str]:
        """
        Runs desktop OAuth consent flow in local browser.
        Returns (success: bool, message: str).
        """
        creds_file = client_secrets_file or self.credentials_path
        if not creds_file.exists():
            return False, f"Credentials file not found at: {creds_file}. Please configure it in Settings."

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_file),
                DRIVE_SCOPES
            )
            # Run local server to catch OAuth callback redirect
            creds = flow.run_local_server(port=port, prompt="consent", access_type="offline")
            self._credentials = creds
            self._save_token(creds)
            self.fetch_account_info()
            logger.info("OAuth login completed successfully.")
            return True, "Login successful"
        except Exception as e:
            err_msg = f"OAuth authentication failed: {str(e)}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg

    def logout(self) -> bool:
        """Logs out user, deletes local token, and clears memory session."""
        try:
            if self._credentials and self._credentials.token:
                # Optionally revoke token
                try:
                    import requests
                    requests.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": self._credentials.token},
                        headers={"content-type": "application/x-www-form-urlencoded"},
                        timeout=5.0
                    )
                except Exception as rev_err:
                    logger.debug(f"Token revocation request returned: {rev_err}")

            self._credentials = None
            self._user_profile = {}

            if self.token_path.exists():
                os.remove(self.token_path)
                logger.info(f"Removed saved token at {self.token_path}")

            return True
        except Exception as e:
            logger.error(f"Error logging out: {e}")
            return False

    def fetch_account_info(self) -> Dict[str, Any]:
        """Fetches user profile and Drive storage quota from Google Drive API."""
        if not self.is_authenticated():
            return {}

        try:
            service = build("drive", "v3", credentials=self._credentials, cache_discovery=False)
            about = service.about().get(fields="user,storageQuota").execute()
            
            user = about.get("user", {})
            quota = about.get("storageQuota", {})
            
            self._user_profile = {
                "display_name": user.get("displayName", "Google User"),
                "email": user.get("emailAddress", ""),
                "photo_link": user.get("photoLink", ""),
                "quota_limit": int(quota.get("limit", 0)),
                "quota_usage": int(quota.get("usage", 0)),
                "quota_usage_in_drive": int(quota.get("usageInDrive", 0)),
            }
            return self._user_profile
        except Exception as e:
            logger.warning(f"Could not fetch account info: {e}")
            return self._user_profile

    def get_user_profile(self) -> Dict[str, Any]:
        """Returns cached user profile."""
        return self._user_profile

    def _save_token(self, creds: Credentials):
        """Persists credentials to token.json securely."""
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        logger.debug(f"Saved token to {self.token_path}")
