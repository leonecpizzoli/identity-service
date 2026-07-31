from identity_service.application.dto.commands import LoginCommand
from identity_service.application.dto.outputs import AccessTokenOutput, BuyerOutput
from identity_service.application.ports.output.buyer_repository import BuyerRepository
from identity_service.application.ports.output.password_hasher import PasswordHasher
from identity_service.application.ports.output.token_issuer import TokenIssuer
from identity_service.domain.exceptions.errors import InvalidCredentialsError, ValidationError
from identity_service.domain.value_objects.email import Email


class AuthenticateBuyer:
    def __init__(
        self,
        repository: BuyerRepository,
        password_hasher: PasswordHasher,
        token_issuer: TokenIssuer,
    ) -> None:
        self._repository = repository
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    async def execute(self, command: LoginCommand) -> AccessTokenOutput:
        try:
            email = Email(command.email)
        except ValidationError as error:
            raise InvalidCredentialsError("invalid email or password") from error
        buyer = await self._repository.find_by_email(email)
        if buyer is None or not self._password_hasher.verify(command.password, buyer.password_hash):
            raise InvalidCredentialsError("invalid email or password")
        buyer.ensure_can_authenticate()
        token = self._token_issuer.issue(buyer)
        return AccessTokenOutput(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=BuyerOutput.from_entity(buyer),
        )
