"""
Secure credential encryption utilities for VaultMind enterprise authentication
"""

import os
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional

class SecureCredentialManager:
    """Manages encrypted storage of authentication credentials"""
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize with master key or generate one"""
        if master_key:
            self.key = self._derive_key(master_key.encode())
        else:
            # Use environment variable or generate key
            master_key = os.getenv('VAULTMIND_MASTER_KEY', self._generate_master_key())
            self.key = self._derive_key(master_key.encode())
        
        self.cipher_suite = Fernet(self.key)
    
    def _generate_master_key(self) -> str:
        """Generate a new master key"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    def _derive_key(self, password: bytes) -> bytes:
        """Derive encryption key from password"""
        salt = b'vaultmind_salt_2024'  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary"""
        json_data = json.dumps(credentials)
        encrypted_data = self.cipher_suite.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_credentials(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt credentials dictionary"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            raise ValueError(f"Failed to decrypt credentials: {str(e)}")
    
    def encrypt_string(self, data: str) -> str:
        """Encrypt a single string"""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """Decrypt a single string"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt string: {str(e)}")

# Global instance
credential_manager = SecureCredentialManager()
