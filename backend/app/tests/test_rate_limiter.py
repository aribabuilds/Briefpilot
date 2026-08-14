"""Pure tests for services/rate_limiter.py::RateLimiter -- no FastAPI, no
real clock, just an injected `now` against a fixed max_requests/window."""

from app.services.rate_limiter import RateLimiter


def test_allows_requests_up_to_the_limit() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=1.0) is True
    assert limiter.allow("ip", now=2.0) is True


def test_rejects_the_request_that_exceeds_the_limit() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=60)
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=1.0) is True
    assert limiter.allow("ip", now=2.0) is False


def test_a_request_becomes_allowed_again_once_the_window_slides_past_it() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=5.0) is False  # still within the 10s window
    assert limiter.allow("ip", now=10.1) is True  # the first hit has aged out


def test_different_keys_are_tracked_independently() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("ip-a", now=0.0) is True
    assert limiter.allow("ip-b", now=0.0) is True  # a different key, own budget
    assert limiter.allow("ip-a", now=1.0) is False  # ip-a's budget is spent


def test_a_rejected_request_does_not_consume_the_budget() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=1.0) is False
    assert limiter.allow("ip", now=2.0) is False  # still rejected, not double-counted


def test_allow_now_uses_a_real_clock_and_does_not_raise() -> None:
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    assert limiter.allow_now("ip") is True
