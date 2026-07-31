from prometheus_client import CollectorRegistry, Counter, Histogram


class ServiceMetrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.registry = registry
        self.http_requests_total = Counter(
            "http_requests_total",
            "http requests",
            ["method", "path", "status"],
            registry=registry,
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "http request duration",
            ["method", "path"],
            registry=registry,
        )
        self.http_errors_total = Counter(
            "http_errors_total",
            "http errors",
            ["code"],
            registry=registry,
        )
        self.auth_register_total = Counter(
            "auth_register_total",
            "buyer registrations",
            ["result"],
            registry=registry,
        )
        self.auth_login_total = Counter(
            "auth_login_total",
            "login attempts",
            ["result"],
            registry=registry,
        )
        self.conflicts_total = Counter(
            "conflicts_total",
            "domain conflicts",
            ["code"],
            registry=registry,
        )
