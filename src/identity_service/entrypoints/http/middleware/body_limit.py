import json
from datetime import UTC, datetime

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from identity_service.infrastructure.observability.correlation import current_correlation_id


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self._app = app
        self._max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await _reject(scope, send, 400, "INVALID_CONTENT_LENGTH")
                return
            if declared_size > self._max_body_bytes:
                await _reject(scope, send, 413, "REQUEST_BODY_TOO_LARGE")
                return
        await self._app(scope, receive, send)


async def _reject(scope: Scope, send: Send, status_code: int, code: str) -> None:
    body = json.dumps(
        {
            "code": code,
            "message": "request was rejected",
            "timestamp": datetime.now(UTC).isoformat(),
            "path": scope["path"],
            "correlation_id": current_correlation_id(),
            "field_errors": [],
        }
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
