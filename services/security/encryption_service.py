"""Encryption service for securing sensitive data in Celery tasks."""

import base64
import json
import os
from typing import Any, Dict

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self):
        """Initialize encryption service with key from environment."""
        key = os.environ.get("CELERY_ENCRYPTION_KEY")
        if not key:
            raise ValueError("CELERY_ENCRYPTION_KEY environment variable not set")

        # Handle both base64-encoded keys and raw keys
        if len(key) == 44:  # Base64-encoded Fernet key
            self.fernet = Fernet(key.encode())
        else:  # Raw key - pad/truncate to 32 bytes and encode
            padded_key = key.encode()[:32].ljust(32, b"\0")
            encoded_key = base64.urlsafe_b64encode(padded_key)
            self.fernet = Fernet(encoded_key)

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary to string.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted string
        """
        json_data = json.dumps(data, sort_keys=True)
        encrypted_bytes = self.fernet.encrypt(json_data.encode())
        return encrypted_bytes.decode()

    def decrypt_dict(self, encrypted: str) -> Dict[str, Any]:
        """Decrypt string back to dictionary.

        Args:
            encrypted: Encrypted string

        Returns:
            Decrypted dictionary
        """
        decrypted_bytes = self.fernet.decrypt(encrypted.encode())
        json_data = decrypted_bytes.decode()
        return json.loads(json_data)
