"""Security primitives: password hashing, JWT, AES-GCM, RSA signing.

Everything here is built on well-audited primitives (bcrypt, PyJWT,
``cryptography``). Key material is derived from ``SECRET_KEY`` for symmetric
operations; the server RSA keypair is generated once and persisted under
``KEYS_DIR``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "iat": now, "exp": expires}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid token") from exc


# ---------------------------------------------------------------------------
# Symmetric encryption (AES-256-GCM) for PII at rest
# ---------------------------------------------------------------------------


def _symmetric_key() -> bytes:
    """Derive a stable 32-byte AES key from the app secret."""
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"veriunlearn-pii")
    return hkdf.derive(settings.SECRET_KEY.encode("utf-8"))


def aes_encrypt(plaintext: str) -> str:
    """Encrypt a string; returns ``b64(nonce) . b64(ciphertext)``."""
    nonce = os.urandom(12)
    ciphertext = AESGCM(_symmetric_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"{base64.b64encode(nonce).decode()}.{base64.b64encode(ciphertext).decode()}"


def aes_decrypt(token: str) -> str:
    try:
        nonce_b64, cipher_b64 = token.split(".")
        nonce = base64.b64decode(nonce_b64)
        ciphertext = base64.b64decode(cipher_b64)
        plaintext = AESGCM(_symmetric_key()).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as exc:  # noqa: BLE001 - decryption must never crash the API
        raise ValueError("Failed to decrypt value") from exc


# ---------------------------------------------------------------------------
# RSA digital signatures
# ---------------------------------------------------------------------------


def _load_or_create_keypair() -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    priv_path: Path = settings.SERVER_PRIVATE_KEY_PATH
    pub_path: Path = settings.SERVER_PUBLIC_KEY_PATH
    if priv_path.exists() and pub_path.exists():
        private_key = serialization.load_pem_private_key(
            priv_path.read_bytes(), password=None
        )
        public_key = serialization.load_pem_public_key(pub_path.read_bytes())
        assert isinstance(private_key, rsa.RSAPrivateKey)
        assert isinstance(public_key, rsa.RSAPublicKey)
        return private_key, public_key

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=settings.RSA_KEY_BITS)
    public_key = private_key.public_key()
    priv_path.parent.mkdir(parents=True, exist_ok=True)
    priv_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub_path.write_bytes(
        public_key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    return private_key, public_key


def sign_sha256(message: bytes) -> str:
    """Return base64 RSA-PKCS1v15 signature of ``message``."""
    private_key, _ = _load_or_create_keypair()
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def verify_sha256(message: bytes, signature_b64: str) -> bool:
    _, public_key = _load_or_create_keypair()
    try:
        public_key.verify(
            base64.b64decode(signature_b64), message, padding.PKCS1v15(), hashes.SHA256()
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def public_key_pem() -> str:
    _, public_key = _load_or_create_keypair()
    return public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
