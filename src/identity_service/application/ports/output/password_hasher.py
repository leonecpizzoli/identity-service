from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, raw_password: str) -> str: ...

    def verify(self, raw_password: str, password_hash: str) -> bool: ...
