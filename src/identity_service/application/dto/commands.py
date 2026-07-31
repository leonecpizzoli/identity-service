from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterBuyerCommand:
    full_name: str
    email: str
    document: str
    phone: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
