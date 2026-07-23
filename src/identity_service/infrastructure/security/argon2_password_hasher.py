from argon2 import PasswordHasher as Argon2Hasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = Argon2Hasher()

    def hash(self, raw_password: str) -> str:
        return self._hasher.hash(raw_password)

    def verify(self, raw_password: str, password_hash: str) -> bool:
        try:
            return self._hasher.verify(password_hash, raw_password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False
