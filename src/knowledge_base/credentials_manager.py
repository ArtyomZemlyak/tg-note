"""
Git Credentials Manager
Securely stores and retrieves per-user Git credentials (GitHub/GitLab tokens)
Uses Fernet symmetric encryption for secure storage
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from cryptography.fernet import Fernet
from filelock import FileLock
from loguru import logger


class CredentialsManager:
    """
    Manages per-user Git credentials with encryption

    Features:
    - Symmetric encryption using Fernet (AES-128)
    - Per-user credential storage
    - Support for GitHub and GitLab
    - Automatic key generation and management
    - Thread-safe with file locking
    """

    def __init__(
        self,
        storage_file: str = "./data/user_credentials.enc",
        key_file: str = "./data/.credentials_key",
    ):
        """
        Initialize credentials manager

        Args:
            storage_file: Path to encrypted credentials storage
            key_file: Path to encryption key file
        """
        self.storage_file = Path(storage_file)
        self.key_file = Path(key_file)
        self.lock_file = Path(str(storage_file) + ".lock")

        # Ensure parent directory exists
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize or load encryption key
        self.cipher_suite = self._initialize_encryption()

        # Initialize storage file if not exists
        if not self.storage_file.exists():
            self._save_encrypted_data({})

        logger.info("Credentials manager initialized")

    def _initialize_encryption(self) -> Fernet:
        """
        Initialize encryption cipher
        Generates new key if it doesn't exist

        Returns:
            Fernet cipher suite
        """
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, "rb") as f:
                key = f.read()
            logger.info("Loaded existing encryption key")
        else:
            # Generate new key
            key = Fernet.generate_key()
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, "wb") as f:
                f.write(key)
            # AICODE-NOTE: Set restrictive permissions on key file (Unix only)
            try:
                self.key_file.chmod(0o600)
            except Exception as e:
                logger.warning(f"Could not set key file permissions: {e}")
            logger.info("Generated new encryption key")

        return Fernet(key)

    def _load_encrypted_data(self) -> Dict:
        """
        Load and decrypt credentials data

        Returns:
            Decrypted credentials dictionary
        """
        with FileLock(self.lock_file):
            try:
                if self.storage_file.exists():
                    with open(self.storage_file, "rb") as f:
                        encrypted_data = f.read()

                    if encrypted_data:
                        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
                        return json.loads(decrypted_data.decode("utf-8"))
            except Exception as e:
                logger.error(f"Error loading encrypted credentials: {e}", exc_info=True)

        return {}

    def _save_encrypted_data(self, data: Dict) -> None:
        """
        Encrypt and save credentials data

        Args:
            data: Credentials dictionary to save
        """
        with FileLock(self.lock_file):
            try:
                json_data = json.dumps(data, indent=2, ensure_ascii=False)
                encrypted_data = self.cipher_suite.encrypt(json_data.encode("utf-8"))

                with open(self.storage_file, "wb") as f:
                    f.write(encrypted_data)

                # AICODE-NOTE: Set restrictive permissions on storage file (Unix only)
                try:
                    self.storage_file.chmod(0o600)
                except Exception as e:
                    logger.warning(f"Could not set storage file permissions: {e}")

            except Exception as e:
                logger.error(f"Error saving encrypted credentials: {e}", exc_info=True)
                raise

    def set_credentials(
        self,
        user_id: int,
        platform: str,
        username: str,
        token: str,
        remote_url: Optional[str] = None,
    ) -> bool:
        """
        Set Git credentials for a user

        Args:
            user_id: User ID
            platform: Platform name ("github" or "gitlab")
            username: Git username
            token: Personal access token
            remote_url: Optional remote URL for reference

        Returns:
            True if successful, False otherwise
        """
        platform = platform.lower()
        if platform not in ("github", "gitlab"):
            logger.error(f"Unsupported platform: {platform}")
            return False

        try:
            data = self._load_encrypted_data()
            user_key = str(user_id)

            if user_key not in data:
                data[user_key] = {}

            data[user_key][platform] = {
                "username": username,
                "token": token,
                "remote_url": remote_url,
            }

            self._save_encrypted_data(data)
            logger.info(
                f"Stored {platform} credentials for user {user_id} (username: {username})"
            )
            return True

        except Exception as e:
            logger.error(f"Error setting credentials for user {user_id}: {e}", exc_info=True)
            return False

    def get_credentials(
        self, user_id: int, platform: str
    ) -> Optional[Tuple[str, str, Optional[str]]]:
        """
        Get Git credentials for a user

        Args:
            user_id: User ID
            platform: Platform name ("github" or "gitlab")

        Returns:
            Tuple of (username, token, remote_url) or None if not found
        """
        platform = platform.lower()
        if platform not in ("github", "gitlab"):
            logger.error(f"Unsupported platform: {platform}")
            return None

        try:
            data = self._load_encrypted_data()
            user_key = str(user_id)

            if user_key in data and platform in data[user_key]:
                creds = data[user_key][platform]
                return (creds["username"], creds["token"], creds.get("remote_url"))

            return None

        except Exception as e:
            logger.error(f"Error getting credentials for user {user_id}: {e}", exc_info=True)
            return None

    def remove_credentials(self, user_id: int, platform: Optional[str] = None) -> bool:
        """
        Remove Git credentials for a user

        Args:
            user_id: User ID
            platform: Platform name ("github" or "gitlab"), or None to remove all

        Returns:
            True if successful, False otherwise
        """
        try:
            data = self._load_encrypted_data()
            user_key = str(user_id)

            if user_key not in data:
                return True  # Nothing to remove

            if platform:
                platform = platform.lower()
                if platform in data[user_key]:
                    del data[user_key][platform]
                    logger.info(f"Removed {platform} credentials for user {user_id}")
            else:
                # Remove all credentials for this user
                del data[user_key]
                logger.info(f"Removed all credentials for user {user_id}")

            # Clean up empty user entries
            if user_key in data and not data[user_key]:
                del data[user_key]

            self._save_encrypted_data(data)
            return True

        except Exception as e:
            logger.error(f"Error removing credentials for user {user_id}: {e}", exc_info=True)
            return False

    def list_credentials(self, user_id: int) -> Dict[str, Dict]:
        """
        List all credentials for a user (without exposing tokens)

        Args:
            user_id: User ID

        Returns:
            Dictionary with platform names as keys and info dicts as values
        """
        try:
            data = self._load_encrypted_data()
            user_key = str(user_id)

            if user_key not in data:
                return {}

            # Return credentials info without tokens
            result = {}
            for platform, creds in data[user_key].items():
                result[platform] = {
                    "username": creds["username"],
                    "remote_url": creds.get("remote_url"),
                    "token_set": bool(creds.get("token")),
                }

            return result

        except Exception as e:
            logger.error(f"Error listing credentials for user {user_id}: {e}", exc_info=True)
            return {}

    def get_credentials_for_url(
        self, user_id: int, remote_url: str
    ) -> Optional[Tuple[str, str, str]]:
        """
        Get credentials for a specific remote URL

        Args:
            user_id: User ID
            remote_url: Git remote URL

        Returns:
            Tuple of (platform, username, token) or None if not found
        """
        # Detect platform from URL
        remote_url_lower = remote_url.lower()

        if "github.com" in remote_url_lower:
            platform = "github"
        elif "gitlab.com" in remote_url_lower or "gitlab" in remote_url_lower:
            platform = "gitlab"
        else:
            logger.warning(f"Could not detect platform from URL: {remote_url}")
            return None

        creds = self.get_credentials(user_id, platform)
        if creds:
            username, token, _ = creds
            return (platform, username, token)

        return None

    def has_credentials(self, user_id: int, platform: Optional[str] = None) -> bool:
        """
        Check if user has credentials stored

        Args:
            user_id: User ID
            platform: Optional platform name to check specifically

        Returns:
            True if credentials exist, False otherwise
        """
        try:
            data = self._load_encrypted_data()
            user_key = str(user_id)

            if user_key not in data:
                return False

            if platform:
                return platform.lower() in data[user_key]
            else:
                return bool(data[user_key])

        except Exception as e:
            logger.error(f"Error checking credentials for user {user_id}: {e}", exc_info=True)
            return False
