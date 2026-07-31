import pytest

from identity_service.domain.exceptions.errors import ValidationError
from identity_service.domain.services.password_policy import PasswordPolicy


def test_accepts_strong_password() -> None:
    PasswordPolicy.ensure_strong("Str0ngPassword")


@pytest.mark.parametrize(
    "raw",
    [
        "Sh0rt",
        "alllowercase1",
        "ALLUPPERCASE1",
        "NoDigitsHere",
        "A1" + "a" * 200,
    ],
)
def test_rejects_weak_password(raw: str) -> None:
    with pytest.raises(ValidationError):
        PasswordPolicy.ensure_strong(raw)
