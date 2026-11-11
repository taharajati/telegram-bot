"""
Application-level encryption for sensitive bank data.
AES-256-GCM with key derived from ENCRYPTION_KEY env var.

This module is used by the Python bot to encrypt bank card info
before storing in DB. The Next.js website reads it using its
own crypto.ts (Node.js) with the same ENCRYPTION_KEY.

Usage:
    from utils.crypto import safe_encrypt, safe_decrypt
    
    shop.card_number = safe_encrypt("6037991234567890")  # encrypted
    display = safe_decrypt(shop.card_number)  # decrypted
"""
import base64
import hashlib
import os
import secrets

_KEY = None

def _get_key() -> bytes:
    """Derive a 256-bit key from ENCRYPTION_KEY env var."""
    global _KEY
    if _KEY is not None:
        return _KEY
    master = os.environ.get('ENCRYPTION_KEY', '')
    if len(master) < 32:
        raise RuntimeError(
            'ENCRYPTION_KEY environment variable must be set (min 32 chars). '
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
    _KEY = hashlib.scrypt(master.encode(), salt=b'foroshgram-salt', n=16384, r=8, p=1, dklen=32)
    return _KEY


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext → base64(iv + ciphertext + auth_tag)."""
    key = _get_key()
    # Use os.urandom for IV (12 bytes for GCM)
    iv = os.urandom(12)
    
    # AES-GCM via cryptography if available, else fallback to pure python
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        ciphertext_with_tag = aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
        # ciphertext_with_tag = ciphertext + auth_tag (last 16 bytes)
        return base64.b64encode(iv + ciphertext_with_tag).decode('ascii')
    except ImportError:
        pass
    
    # Fallback: AES-GCM with manual encrypt using PyCryptodome
    try:
        from Crypto.Cipher import AES as _AES
        cipher = _AES.new(key, _AES.MODE_GCM, nonce=iv)
        ciphertext, auth_tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        return base64.b64encode(iv + ciphertext + auth_tag).decode('ascii')
    except ImportError:
        raise RuntimeError(
            'Neither cryptography nor PyCryptodome is installed. '
            'Install one: pip install cryptography'
        )


def decrypt(encrypted_b64: str) -> str:
    """Decrypt base64 string → plaintext."""
    key = _get_key()
    data = base64.b64decode(encrypted_b64)
    
    if len(data) < 12 + 16 + 1:  # IV + auth_tag + min 1 byte ciphertext
        raise ValueError('Invalid encrypted data length')
    
    iv = data[:12]
    auth_tag = data[-16:]
    ciphertext = data[12:-16]
    
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(iv, ciphertext + auth_tag, None).decode('utf-8')
    except ImportError:
        pass
    
    try:
        from Crypto.Cipher import AES as _AES
        cipher = _AES.new(key, _AES.MODE_GCM, nonce=iv)
        return cipher.decrypt_and_verify(ciphertext, auth_tag).decode('utf-8')
    except ImportError:
        raise RuntimeError('Neither cryptography nor PyCryptodome is installed.')


def is_encrypted(value: str) -> bool:
    """Check if a string looks like it's already encrypted (base64, correct length)."""
    if not value:
        return False
    try:
        data = base64.b64decode(value)
        return len(data) >= 12 + 16 + 1  # IV + auth_tag + min 1 byte
    except Exception:
        return False


def safe_decrypt(value: str | None) -> str | None:
    """Get: decrypts if encrypted, returns plaintext. Safe for display."""
    if not value:
        return None
    if is_encrypted(value):
        try:
            return decrypt(value)
        except Exception:
            return value  # fallback for legacy data
    return value  # already plaintext


def safe_encrypt(value: str | None) -> str | None:
    """Set: always encrypts non-empty values. Idempotent."""
    if not value:
        return None
    if is_encrypted(value):
        return value  # already encrypted
    return encrypt(value)
