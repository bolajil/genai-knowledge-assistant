"""
Enterprise Encryption Utilities
===============================

Provides encryption/decryption utilities for sensitive data handling.
Uses AES-256 encryption with proper key management for enterprise security.
"""

import os
import base64
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey
from typing import Optional

logger = logging.getLogger(__name__)

class EnterpriseEncryption:
    """
    Enterprise-grade encryption using AES-256 with PBKDF2 key derivation.

    Features:
    - AES-256-GCM encryption
    - PBKDF2 key derivation with salt
    - Secure random IV generation
    - Authentication tags for integrity
    """

    def __init__(self, key: Optional[bytes] = None, salt_size: int = 32, iterations: int = 100000):
        """
        Initialize encryption with optional master key.

        Args:
            key: Optional master key (32 bytes for AES-256)
            salt_size: Size of salt for key derivation
            iterations: PBKDF2 iterations for key stretching
        """
        self.salt_size = salt_size
        self.iterations = iterations

        # Use provided key or generate from environment
        if key:
            self.master_key = key
        else:
            # Get key from environment or generate one
            key_b64 = os.getenv("ENCRYPTION_KEY")
            if key_b64:
                try:
                    self.master_key = base64.b64decode(key_b64)
                    if len(self.master_key) != 32:
                        raise ValueError("Encryption key must be 32 bytes (256 bits)")
                except Exception as e:
                    logger.error(f"Invalid encryption key in environment: {e}")
                    self.master_key = self._generate_key()
            else:
                logger.warning("No encryption key provided, generating temporary key")
                self.master_key = self._generate_key()

    def _generate_key(self) -> bytes:
        """Generate a secure random key"""
        return os.urandom(32)

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master key and salt using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        return kdf.derive(self.master_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64 encoded encrypted data with salt and IV
        """
        try:
            # Generate salt and IV
            salt = os.urandom(self.salt_size)
            iv = os.urandom(16)  # AES block size

            # Derive key
            key = self._derive_key(salt)

            # Encrypt using AES-GCM
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()

            # Convert to bytes and encrypt
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = encryptor.update(plaintext_bytes) + encryptor.finalize()

            # Combine: salt + iv + tag + ciphertext
            encrypted_data = salt + iv + encryptor.tag + ciphertext

            # Base64 encode for storage
            return base64.b64encode(encrypted_data).decode('utf-8')

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt encrypted string.

        Args:
            encrypted_data: Base64 encoded encrypted data

        Returns:
            Decrypted plaintext string
        """
        try:
            # Base64 decode
            encrypted_bytes = base64.b64decode(encrypted_data)

            # Extract components
            salt = encrypted_bytes[:self.salt_size]
            iv = encrypted_bytes[self.salt_size:self.salt_size + 16]
            tag = encrypted_bytes[self.salt_size + 16:self.salt_size + 32]
            ciphertext = encrypted_bytes[self.salt_size + 32:]

            # Derive key
            key = self._derive_key(salt)

            # Decrypt using AES-GCM
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()

            plaintext_bytes = decryptor.update(ciphertext) + decryptor.finalize()

            return plaintext_bytes.decode('utf-8')

        except InvalidKey:
            logger.error("Decryption failed: Invalid key or corrupted data")
            raise ValueError("Invalid encryption key or corrupted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def health_check(self) -> bool:
        """Perform health check on encryption system"""
        try:
            test_data = "encryption_test_data"
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_data
        except Exception as e:
            logger.error(f"Encryption health check failed: {e}")
            return False


# Global encryption instance
_encryption_instance = None

def get_encryption() -> EnterpriseEncryption:
    """Get singleton encryption instance"""
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = EnterpriseEncryption()
    return _encryption_instance

# Convenience functions
def encrypt_data(data: str) -> str:
    """Encrypt data using enterprise encryption"""
    enc = get_encryption()
    return enc.encrypt(data)

def decrypt_data(data: str) -> str:
    """Decrypt data using enterprise encryption"""
    enc = get_encryption()
    return enc.decrypt(data)

def test_encryption():
    """Test encryption functionality"""
    enc = get_encryption()

    test_cases = [
        "Simple text",
        "Text with special characters: !@#$%^&*()",
        "Unicode: 你好世界 🌍",
        "Long text " * 1000,
        "",
        "A"
    ]

    print("Testing encryption/decryption...")
    for i, test_data in enumerate(test_cases):
        try:
            encrypted = enc.encrypt(test_data)
            decrypted = enc.decrypt(encrypted)

            if decrypted == test_data:
                print(f"✅ Test {i+1} passed")
            else:
                print(f"❌ Test {i+1} failed: data mismatch")
                return False

        except Exception as e:
            print(f"❌ Test {i+1} failed with exception: {e}")
            return False

    print("🎉 All encryption tests passed!")
    return True

if __name__ == "__main__":
    test_encryption()
