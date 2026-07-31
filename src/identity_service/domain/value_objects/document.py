import re
from dataclasses import dataclass

from identity_service.domain.exceptions.errors import ValidationError

_DOCUMENT_PATTERN = re.compile(r"^[A-Z0-9]{5,32}$")


@dataclass(frozen=True, slots=True)
class Document:
    value: str

    def __post_init__(self) -> None:
        normalized = re.sub(r"[^A-Za-z0-9]", "", self.value).upper()
        if not _DOCUMENT_PATTERN.fullmatch(normalized):
            raise ValidationError("identification document is invalid", field="document")
        object.__setattr__(self, "value", normalized)
