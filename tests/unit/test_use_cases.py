from datetime import UTC, datetime
from itertools import count

import pytest

from identity_service.application.dto.commands import LoginCommand, RegisterBuyerCommand
from identity_service.application.dto.outputs import IssuedToken
from identity_service.application.use_cases.authenticate_buyer import AuthenticateBuyer
from identity_service.application.use_cases.get_authenticated_buyer import GetAuthenticatedBuyer
from identity_service.application.use_cases.register_buyer import RegisterBuyer
from identity_service.domain.entities.buyer import Buyer
from identity_service.domain.enums.account_status import AccountStatus
from identity_service.domain.enums.role import Role
from identity_service.domain.exceptions.errors import (
    AccountNotActiveError,
    BuyerNotFoundError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    ValidationError,
)
from identity_service.domain.value_objects.buyer_id import BuyerId
from identity_service.domain.value_objects.email import Email

_NOW = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)


class InMemoryBuyerRepository:
    def __init__(self) -> None:
        self.buyers: list[Buyer] = []

    async def insert(self, buyer: Buyer) -> None:
        if any(existing.email == buyer.email for existing in self.buyers):
            raise EmailAlreadyRegisteredError("email is already registered")
        self.buyers.append(buyer)

    async def find_by_email(self, email: Email) -> Buyer | None:
        return next((buyer for buyer in self.buyers if buyer.email == email), None)

    async def find_by_id(self, buyer_id: BuyerId) -> Buyer | None:
        return next((buyer for buyer in self.buyers if buyer.id == buyer_id), None)


class FakePasswordHasher:
    def hash(self, raw_password: str) -> str:
        return f"hash::{raw_password}"

    def verify(self, raw_password: str, password_hash: str) -> bool:
        return password_hash == f"hash::{raw_password}"


class FixedClock:
    def now(self) -> datetime:
        return _NOW


class SequentialIdProvider:
    def __init__(self) -> None:
        self._counter = count(1)

    def new_id(self) -> str:
        return f"{next(self._counter):032x}"


class FakeTokenIssuer:
    def issue(self, buyer: Buyer) -> IssuedToken:
        return IssuedToken(
            access_token=f"token-for-{buyer.id.value}", token_type="bearer", expires_in=900
        )


def make_register_use_case(
    repository: InMemoryBuyerRepository | None = None,
) -> tuple[RegisterBuyer, InMemoryBuyerRepository]:
    repo = repository or InMemoryBuyerRepository()
    return RegisterBuyer(repo, FakePasswordHasher(), FixedClock(), SequentialIdProvider()), repo


def make_command(
    email: str = "ana@example.com", document: str = "12345678909"
) -> RegisterBuyerCommand:
    return RegisterBuyerCommand(
        full_name="Ana Souza",
        email=email,
        document=document,
        phone="+5511912345678",
        password="Str0ngPassword",
    )


async def test_register_creates_buyer_with_buyer_role_and_hashed_password() -> None:
    use_case, repository = make_register_use_case()
    output = await use_case.execute(make_command())
    stored = repository.buyers[0]
    assert output.roles == ("BUYER",)
    assert output.status == "ACTIVE"
    assert stored.password_hash == "hash::Str0ngPassword"
    assert stored.email.value == "ana@example.com"
    assert not hasattr(output, "password_hash")


async def test_register_rejects_weak_password_before_persisting() -> None:
    use_case, repository = make_register_use_case()
    command = RegisterBuyerCommand(
        full_name="Ana Souza",
        email="ana@example.com",
        document="12345678909",
        phone="+5511912345678",
        password="weak",
    )
    with pytest.raises(ValidationError):
        await use_case.execute(command)
    assert repository.buyers == []


async def test_register_propagates_duplicate_email_conflict() -> None:
    use_case, _ = make_register_use_case()
    await use_case.execute(make_command())
    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(make_command(document="98765432100"))


async def test_login_returns_token_for_valid_credentials() -> None:
    register, repository = make_register_use_case()
    await register.execute(make_command())
    authenticate = AuthenticateBuyer(repository, FakePasswordHasher(), FakeTokenIssuer())
    output = await authenticate.execute(
        LoginCommand(email="ANA@example.com", password="Str0ngPassword")
    )
    assert output.access_token.startswith("token-for-")
    assert output.token_type == "bearer"
    assert output.expires_in == 900
    assert output.user.email == "ana@example.com"


async def test_login_rejects_wrong_password() -> None:
    register, repository = make_register_use_case()
    await register.execute(make_command())
    authenticate = AuthenticateBuyer(repository, FakePasswordHasher(), FakeTokenIssuer())
    with pytest.raises(InvalidCredentialsError):
        await authenticate.execute(LoginCommand(email="ana@example.com", password="Wrong1234x"))


async def test_login_rejects_unknown_email_and_malformed_email() -> None:
    authenticate = AuthenticateBuyer(
        InMemoryBuyerRepository(), FakePasswordHasher(), FakeTokenIssuer()
    )
    with pytest.raises(InvalidCredentialsError):
        await authenticate.execute(LoginCommand(email="ghost@example.com", password="Whatever12"))
    with pytest.raises(InvalidCredentialsError):
        await authenticate.execute(LoginCommand(email="not-an-email", password="Whatever12"))


@pytest.mark.parametrize("status", [AccountStatus.INACTIVE, AccountStatus.BLOCKED])
async def test_login_rejects_non_active_account(status: AccountStatus) -> None:
    register, repository = make_register_use_case()
    await register.execute(make_command())
    repository.buyers[0].status = status
    authenticate = AuthenticateBuyer(repository, FakePasswordHasher(), FakeTokenIssuer())
    with pytest.raises(AccountNotActiveError):
        await authenticate.execute(LoginCommand(email="ana@example.com", password="Str0ngPassword"))


async def test_get_authenticated_buyer_returns_profile() -> None:
    register, repository = make_register_use_case()
    created = await register.execute(make_command())
    use_case = GetAuthenticatedBuyer(repository)
    output = await use_case.execute(created.id)
    assert output.email == "ana@example.com"
    assert Role.BUYER.value in output.roles


async def test_get_authenticated_buyer_rejects_unknown_id() -> None:
    use_case = GetAuthenticatedBuyer(InMemoryBuyerRepository())
    with pytest.raises(BuyerNotFoundError):
        await use_case.execute("f" * 32)
