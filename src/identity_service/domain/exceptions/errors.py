class DomainError(Exception):
    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    code = "VALIDATION_ERROR"

    def __init__(self, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field


class EmailAlreadyRegisteredError(DomainError):
    code = "EMAIL_ALREADY_REGISTERED"


class DocumentAlreadyRegisteredError(DomainError):
    code = "DOCUMENT_ALREADY_REGISTERED"


class RegistrationConflictError(DomainError):
    code = "REGISTRATION_CONFLICT"


class InvalidCredentialsError(DomainError):
    code = "INVALID_CREDENTIALS"


class AccountNotActiveError(DomainError):
    code = "ACCOUNT_NOT_ACTIVE"


class BuyerNotFoundError(DomainError):
    code = "BUYER_NOT_FOUND"


class AuthenticationRequiredError(DomainError):
    code = "UNAUTHENTICATED"


class RateLimitExceededError(DomainError):
    code = "RATE_LIMITED"
