from uuid import uuid4


class Uuid4IdProvider:
    def new_id(self) -> str:
        return uuid4().hex
