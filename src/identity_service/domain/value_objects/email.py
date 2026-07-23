import re
from dataclasses import dataclass

from identity_service.domain.exceptions.errors import ValidationError

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized or len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
            raise ValidationError("email address is invalid", field="email")
        object.__setattr__(self, "value", normalized)
