from datetime import UTC, datetime

import pytest

from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.account_status import AccountStatus
from identity_service.domain.enums.role import Role
from identity_service.domain.exceptions.errors import AccountNotActiveError, ValidationError
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.document import Document
from identity_service.domain.value_objects.email import Email
from identity_service.domain.value_objects.phone import Phone

_NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


def make_buyer(
    full_name: str = "Ana Souza",
    status: AccountStatus = AccountStatus.ACTIVE,
    roles: frozenset[Role] = frozenset({Role.BUYER}),
) -> Buyer:
    buyer = Buyer.register(
        buyer_id=BuyerId("a" * 32),
        full_name=full_name,
        email=Email("ana@example.com"),
        document=Document("12345678909"),
        phone=Phone("+5511912345678"),
        password_hash="hashed",
        roles=roles,
        now=_NOW,
    )
    buyer.status = status
    return buyer


def test_register_normalizes_name_and_sets_defaults() -> None:
    buyer = make_buyer(full_name="  Ana   Souza  ")
    assert buyer.full_name == "Ana Souza"
    assert buyer.status is AccountStatus.ACTIVE
    assert buyer.version == 1
    assert buyer.created_at == buyer.updated_at == _NOW


@pytest.mark.parametrize("full_name", ["", "Ana", "  A  "])
def test_register_rejects_invalid_full_name(full_name: str) -> None:
    with pytest.raises(ValidationError):
        make_buyer(full_name=full_name)


def test_register_requires_roles() -> None:
    with pytest.raises(ValidationError):
        make_buyer(roles=frozenset())


def test_active_account_can_authenticate() -> None:
    make_buyer().ensure_can_authenticate()


@pytest.mark.parametrize("status", [AccountStatus.INACTIVE, AccountStatus.BLOCKED])
def test_non_active_account_cannot_authenticate(status: AccountStatus) -> None:
    with pytest.raises(AccountNotActiveError):
        make_buyer(status=status).ensure_can_authenticate()


def test_has_role() -> None:
    buyer = make_buyer(roles=frozenset({Role.BUYER}))
    assert buyer.has_role(Role.BUYER)
    assert not buyer.has_role(Role.ADMIN)
