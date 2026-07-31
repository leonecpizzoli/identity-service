from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from identity_service.infrastructure.observability.correlation import (
    correlation_id_var,
    resolve_correlation_id,
)


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        correlation_id = resolve_correlation_id(headers.get("x-correlation-id"))
        token = correlation_id_var.set(correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["x-correlation-id"] = correlation_id
            await send(message)

        try:
            await self._app(scope, receive, send_with_header)
        finally:
            correlation_id_var.reset(token)
