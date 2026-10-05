import base64
import os
from typing import Literal

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AesGcmSecretEncryptionImpl:
    """
    Реализует SigningSecretEncryption и InvoiceFieldEncryption.
    Формат шифротекста: base64(b"v1:" + nonce(12 bytes) + ciphertext)
    """

    def __init__(
        self,
        key: bytes,
        nonce_size: int,
        version_prefix: Literal[b"v1:"] = b"v1:",
    ) -> None:
        # AESGCM сам валидирует длину ключа (16/24/32 bytes)
        self._aesgcm = AESGCM(key)
        self._nonce_size = nonce_size
        self._version_prefix = version_prefix

    def encrypt(
        self,
        plaintext: str,
    ) -> str:
        nonce = os.urandom(self._nonce_size)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode(), None)
        raw = self._version_prefix + nonce + ciphertext
        return base64.b64encode(raw).decode()

    def decrypt(
        self,
        ciphertext: str,
    ) -> str:
        raw = base64.b64decode(ciphertext.encode())
        if not raw.startswith(self._version_prefix):
            raise ValueError(f"Unsupported encryption version: {raw[:3]!r}")
        payload = raw[len(self._version_prefix) :]
        nonce = payload[: self._nonce_size]
        data = payload[self._nonce_size :]
        return self._aesgcm.decrypt(nonce, data, None).decode()
