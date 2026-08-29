from typing import Protocol


class SigningSecretEncryption(Protocol):
    def encrypt(
        self,
        plaintext: str,
    ) -> str:
        raise NotImplementedError

    def decrypt(
        self,
        ciphertext: str,
    ) -> str:
        raise NotImplementedError
