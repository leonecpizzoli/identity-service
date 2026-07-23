from typing import Protocol


class IdProvider(Protocol):
    def new_id(self) -> str: ...
