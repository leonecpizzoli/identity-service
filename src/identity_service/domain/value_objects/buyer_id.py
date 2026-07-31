import re
from dataclasses import dataclass

from identity_service.domain.exceptions.errors import ValidationError

_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True, slots=True)
class BuyerId:
    value: str

    def __post_init__(self) -> None:
        if not _ID_PATTERN.fullmatch(self.value):
            raise ValidationError("buyer id is invalid", field="buyer_id")
