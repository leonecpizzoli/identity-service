from typing import Protocol

from identity_service.application.dto.outputs import IssuedToken
from identity_service.domain.entities.buyer import Buyer


class TokenIssuer(Protocol):
    def issue(self, buyer: Buyer) -> IssuedToken: ...
