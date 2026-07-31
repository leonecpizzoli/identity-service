import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from identity_service.infrastructure.observability.metrics import ServiceMetrics

_logger = logging.getLogger("identity_service.http")


class HttpMetricsMiddleware:
    def __init__(self, app: ASGIApp, metrics: ServiceMetrics) -> None:
        self._app = app
        self._metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        method = scope["method"]
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_tracking(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, send_with_tracking)
        finally:
            duration_seconds = time.perf_counter() - started_at
            route = scope.get("route")
            path_template = getattr(route, "path", scope["path"])
            self._metrics.http_requests_total.labels(
                method=method, path=path_template, status=str(status_code)
            ).inc()
            self._metrics.http_request_duration_seconds.labels(
                method=method, path=path_template
            ).observe(duration_seconds)
            _logger.info(
                "http_request",
                extra={
                    "event_fields": {
                        "method": method,
                        "path": scope["path"],
                        "status_code": status_code,
                        "duration_ms": round(duration_seconds * 1000, 2),
                    }
                },
            )
