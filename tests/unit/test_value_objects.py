import pytest

from identity_service.domain.exceptions.errors import ValidationError
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone


def test_email_is_normalized() -> None:
    assert Email("  Buyer@Example.COM ").value == "buyer@example.com"


@pytest.mark.parametrize("raw", ["", "invalid", "a@b", "user@@example.com", "user@.com"])
def test_email_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        Email(raw)


def test_document_is_normalized() -> None:
    assert Document("123.456.789-09").value == "12345678909"
    assert Document("ab-123456").value == "AB123456"


@pytest.mark.parametrize("raw", ["", "12", "a" * 40, "!!!"])
def test_document_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        Document(raw)


def test_phone_is_normalized_to_e164_style() -> None:
    assert Phone("+55 (11) 91234-5678").value == "+5511912345678"
    assert Phone("5511912345678").value == "+5511912345678"


@pytest.mark.parametrize("raw", ["", "abc", "+0123456", "123", "+123456789012345678"])
def test_phone_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValidationError):
        Phone(raw)


def test_buyer_id_requires_hex_format() -> None:
    assert BuyerId("a" * 32).value == "a" * 32
    with pytest.raises(ValidationError):
        BuyerId("not-an-id")
