from __future__ import annotations

import base64

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder

from app.core.config import settings


class SigningService:
    def __init__(self) -> None:
        self._key_path = settings.resolved_signing_key_path
        self._signing_key: SigningKey | None = None
        self._verify_key: VerifyKey | None = None
        self._load_or_create_key()

    def _load_or_create_key(self) -> None:
        if self._key_path.exists():
            with open(self._key_path, "rb") as f:
                seed = f.read()
            self._signing_key = SigningKey(seed)
        else:
            self._signing_key = SigningKey.generate()
            with open(self._key_path, "wb") as f:
                f.write(self._signing_key.encode())
            self._key_path.chmod(0o600)

        self._verify_key = self._signing_key.verify_key

    @property
    def public_key(self) -> str:
        return self._verify_key.encode(encoder=HexEncoder).decode()

    def sign(self, message: str | bytes) -> str:
        if isinstance(message, str):
            message = message.encode("utf-8")
        signed = self._signing_key.sign(message)
        return base64.b64encode(signed.signature).decode()

    def verify(self, message: str | bytes, signature_b64: str) -> bool:
        if isinstance(message, str):
            message = message.encode("utf-8")
        try:
            signature = base64.b64decode(signature_b64)
            self._verify_key.verify(message, signature)
            return True
        except Exception:
            return False

    def verify_with_key(self, message: str | bytes, signature_b64: str, public_key_hex: str) -> bool:
        if isinstance(message, str):
            message = message.encode("utf-8")
        try:
            verify_key = VerifyKey(bytes.fromhex(public_key_hex))
            signature = base64.b64decode(signature_b64)
            verify_key.verify(message, signature)
            return True
        except Exception:
            return False
