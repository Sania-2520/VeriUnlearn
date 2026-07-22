import logging
from typing import Any, Optional, Tuple

from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives.asymmetric.types import (
    PrivateKeyTypes,
    PublicKeyTypes,
)


class SignatureManager:
    """Cryptographic signature management for deletion proofs."""

    def __init__(self, algorithm: str = "ed25519") -> None:
        self.algorithm = algorithm

    def generate_key_pair(self) -> Tuple[PrivateKeyTypes, PublicKeyTypes]:
        if self.algorithm == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
        elif self.algorithm == "rsa":
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=4096
            )
            public_key = private_key.public_key()
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
        return private_key, public_key

    def sign(self, message: str, private_key: PrivateKeyTypes) -> str:
        message_bytes = message.encode("utf-8")

        if isinstance(private_key, ed25519.Ed25519PrivateKey):
            signature = private_key.sign(message_bytes)
        elif isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                message_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
        else:
            raise ValueError(f"Unsupported key type: {type(private_key)}")

        return signature.hex()

    def verify(
        self,
        message: str,
        signature_hex: str,
        public_key: PublicKeyTypes,
    ) -> bool:
        message_bytes = message.encode("utf-8")
        signature = bytes.fromhex(signature_hex)

        try:
            if isinstance(public_key, ed25519.Ed25519PublicKey):
                public_key.verify(signature, message_bytes)
            elif isinstance(public_key, rsa.RSAPublicKey):
                public_key.verify(
                    signature,
                    message_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH,
                    ),
                    hashes.SHA256(),
                )
            else:
                raise ValueError(f"Unsupported key type: {type(public_key)}")
            return True
        except InvalidSignature:
            logger.warning("Signature verification failed: invalid signature")
            return False
        except Exception:
            logger.exception("Signature verification raised unexpected exception")
            return False

    @staticmethod
    def serialize_public_key(public_key: PublicKeyTypes) -> str:
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    @staticmethod
    def serialize_private_key(
        private_key: PrivateKeyTypes,
        password: Optional[bytes] = None,
    ) -> str:
        encryption = (
            serialization.BestAvailableEncryption(password)
            if password
            else serialization.NoEncryption()
        )
        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption,
        ).decode("utf-8")

    @staticmethod
    def load_public_key(pem_data: str) -> PublicKeyTypes:
        return serialization.load_pem_public_key(pem_data.encode("utf-8"))

    @staticmethod
    def load_private_key(pem_data: str, password: Optional[bytes] = None) -> PrivateKeyTypes:
        return serialization.load_pem_private_key(
            pem_data.encode("utf-8"), password=password
        )
