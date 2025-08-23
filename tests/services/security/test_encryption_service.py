"""Tests for the encryption service."""

import os
from typing import Dict
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from services.security.encryption_service import EncryptionService


class TestEncryptionService:
    """Test cases for EncryptionService."""

    def test_init_missing_key_raises_error(self):
        """Test that missing encryption key raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="CELERY_ENCRYPTION_KEY environment variable not set"
            ):
                EncryptionService()

    def test_init_with_base64_key(self):
        """Test initialization with a base64-encoded Fernet key."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()
            assert service.fernet is not None

    def test_init_with_raw_key(self):
        """Test initialization with a raw key that gets padded/truncated."""
        raw_key = "test-key-123"
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": raw_key}):
            service = EncryptionService()
            assert service.fernet is not None

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            test_data = {
                "provider": "openai",
                "api_key": "sk-test-key-123",
                "model": "gpt-4",
            }

            # Encrypt the data
            encrypted = service.encrypt_dict(test_data)

            # Verify it's actually encrypted (doesn't contain original values)
            assert "sk-test-key-123" not in encrypted
            assert "openai" not in encrypted
            assert isinstance(encrypted, str)

            # Decrypt and verify
            decrypted = service.decrypt_dict(encrypted)
            assert decrypted == test_data

    def test_encrypt_dict_with_complex_data(self):
        """Test encryption with complex nested data structures."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            test_data = {
                "provider": "anthropic",
                "api_key": "sk-ant-api03-xyz",
                "config": {
                    "temperature": 0.0,
                    "max_tokens": 4096,
                    "options": ["streaming", "safety"],
                },
                "metadata": {"user_id": 12345, "timestamp": "2025-07-26T10:30:00Z"},
            }

            encrypted = service.encrypt_dict(test_data)
            decrypted = service.decrypt_dict(encrypted)

            assert decrypted == test_data
            assert decrypted["config"]["temperature"] == 0.0
            assert decrypted["metadata"]["user_id"] == 12345

    def test_encrypt_dict_consistent_output(self):
        """Test that encrypting the same data produces different results (due to IV)."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            test_data = {"api_key": "test-key"}

            encrypted1 = service.encrypt_dict(test_data)
            encrypted2 = service.encrypt_dict(test_data)

            # Different due to random IV
            assert encrypted1 != encrypted2

            # But both decrypt to the same value
            assert service.decrypt_dict(encrypted1) == test_data
            assert service.decrypt_dict(encrypted2) == test_data

    def test_decrypt_invalid_data_raises_error(self):
        """Test that decrypting invalid data raises an error."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            from cryptography.fernet import InvalidToken

            with pytest.raises(InvalidToken):
                service.decrypt_dict("invalid-encrypted-data")

    def test_encrypt_empty_dict(self):
        """Test encryption of empty dictionary."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            test_data: Dict[str, str] = {}
            encrypted = service.encrypt_dict(test_data)
            decrypted = service.decrypt_dict(encrypted)

            assert decrypted == test_data

    def test_encrypt_dict_with_special_characters(self):
        """Test encryption with special characters and unicode."""
        key = Fernet.generate_key().decode()
        with patch.dict(os.environ, {"CELERY_ENCRYPTION_KEY": key}):
            service = EncryptionService()

            test_data = {
                "api_key": "sk-test_key!@#$%^&*()",
                "provider": "openai",
                "description": "Test with émojis 🚀 and üñíçödé",
            }

            encrypted = service.encrypt_dict(test_data)
            decrypted = service.decrypt_dict(encrypted)

            assert decrypted == test_data
            assert "🚀" in decrypted["description"]
