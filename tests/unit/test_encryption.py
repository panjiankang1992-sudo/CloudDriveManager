"""Unit tests for src/core/encryption.py"""

import pytest
from cryptography.fernet import Fernet

from src.core import encryption as enc
from src.core.exceptions import (
    EncryptionKeyNotSetError,
    EncryptionDecryptError,
    EncryptionEncryptError,
)


class TestEncryptionConfigure:
    def setup_method(self):
        """Reset Fernet state before each test."""
        enc._fernet = None

    def teardown_method(self):
        enc._fernet = None

    def test_configure_with_valid_key(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)
        assert enc._fernet is not None

    def test_configure_with_empty_key_raises(self):
        with pytest.raises(EncryptionKeyNotSetError) as exc_info:
            enc.configure("")
        assert exc_info.value.CODE == "ENCRYPTION_KEY_NOT_SET"

    def test_configure_with_whitespace_key_raises(self):
        with pytest.raises(EncryptionKeyNotSetError):
            enc.configure("   ")


class TestEncryptDecrypt:
    def setup_method(self):
        enc._fernet = None

    def teardown_method(self):
        enc._fernet = None

    def test_encrypt_then_decrypt_returns_original(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)

        original = "Hello, Cloud Drive Manager!"
        ciphertext = enc.encrypt(original)
        decrypted = enc.decrypt(ciphertext)

        assert decrypted == original
        assert ciphertext != original

    def test_encrypt_empty_string(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)

        ciphertext = enc.encrypt("")
        decrypted = enc.decrypt(ciphertext)
        assert decrypted == ""

    def test_encrypt_unicode_string(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)

        original = "中文测试 🎉 密码"
        ciphertext = enc.encrypt(original)
        decrypted = enc.decrypt(ciphertext)
        assert decrypted == original

    def test_encrypt_produces_different_ciphertext_each_time(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)

        plaintext = "same text"
        ct1 = enc.encrypt(plaintext)
        ct2 = enc.encrypt(plaintext)
        # Fernet uses random IV, so ciphertexts differ
        assert ct1 != ct2
        # But both decrypt to same plaintext
        assert enc.decrypt(ct1) == enc.decrypt(ct2) == plaintext

    def test_encrypt_without_configure_raises(self):
        enc._fernet = None
        with pytest.raises(EncryptionKeyNotSetError):
            enc.encrypt("test")

    def test_decrypt_without_configure_raises(self):
        enc._fernet = None
        with pytest.raises(EncryptionKeyNotSetError):
            enc.decrypt("someciphertext")

    def test_decrypt_invalid_ciphertext_raises(self):
        key = Fernet.generate_key().decode()
        enc.configure(key)

        with pytest.raises(EncryptionDecryptError):
            enc.decrypt("invalid_token_not_base64")
