import re
from dataclasses import dataclass

from identity_service.domain.exceptions.errors import ValidationError

_PHONE_PATTERN = re.compile(r"^\+?[1-9][0-9]{7,14}$")


@dataclass(frozen=True, slots=True)
class Phone:
    value: str

    def __post_init__(self) -> None:
        normalized = re.sub(r"[\s().-]", "", self.value.strip())
        if not _PHONE_PATTERN.fullmatch(normalized):
            raise ValidationError("phone number is invalid", field="phone")
        if not normalized.startswith("+"):
            normalized = f"+{normalized}"
        object.__setattr__(self, "value", normalized)
