"""Crypto — byte-compatible with PHP core/Crypto.php.

AES-256-CBC via the `cryptography` library. Stored format:
    enc:v1:<base64(iv)>.<base64(ciphertext)>
Key = sha256(APP_ENCRYPTION_KEY or fallback). decrypt() passes through any
value without the prefix (legacy plaintext). PKCS7 padding (OpenSSL default).
"""
import base64
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from web.backend.core.config import get_cms_settings

_PREFIX = "enc:v1:"
_FALLBACK = "hexacms-default-key-change-me"


def _key_bytes() -> bytes:
    settings = get_cms_settings()
    base = settings.app_encryption_key or settings.encryption_key or ""
    if not base:
        base = _FALLBACK
    return hashlib.sha256(base.encode("utf-8")).digest()


def encrypt(plain: str) -> str:
    """Encrypt a string → 'enc:v1:<iv>.<data>' ('' for empty input)."""
    if plain == "":
        return ""
    import os
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plain.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(_key_bytes()), modes.CBC(iv))
    enc = cipher.encryptor()
    ct = enc.update(padded) + enc.finalize()
    return _PREFIX + base64.b64encode(iv).decode() + "." + base64.b64encode(ct).decode()


def decrypt(value: str) -> str:
    """Decrypt 'enc:v1:...'; pass through legacy plaintext; '' on failure."""
    if value == "":
        return ""
    if not value.startswith(_PREFIX):
        return value
    body = value[len(_PREFIX):]
    parts = body.split(".", 1)
    if len(parts) != 2:
        return ""
    try:
        iv = base64.b64decode(parts[0], validate=True)
        data = base64.b64decode(parts[1], validate=True)
    except Exception:
        return ""
    if len(iv) != 16:
        return ""
    try:
        cipher = Cipher(algorithms.AES(_key_bytes()), modes.CBC(iv))
        dec = cipher.decryptor()
        padded = dec.update(data) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        plain = unpadder.update(padded) + unpadder.finalize()
        return plain.decode("utf-8")
    except Exception:
        return ""


def is_encrypted(value: str) -> bool:
    return value.startswith(_PREFIX)


def mask(value: str) -> str:
    if value == "":
        return ""
    return "••••••••••••" + value[-4:]
