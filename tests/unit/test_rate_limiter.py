from identity_service.infrastructure.security.rate_limiter import SlidingWindowRateLimiter


def test_allows_up_to_limit_then_blocks() -> None:
    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=60.0)
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert not limiter.allow("client")


def test_limits_are_isolated_per_key() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=60.0)
    assert limiter.allow("first")
    assert not limiter.allow("first")
    assert limiter.allow("second")


def test_window_expiry_releases_capacity() -> None:
    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=0.0)
    assert limiter.allow("client")
    assert limiter.allow("client")
