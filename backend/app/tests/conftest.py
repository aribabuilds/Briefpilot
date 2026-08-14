"""Shared fixtures for the whole backend test suite."""

from collections.abc import Iterator

import pytest

from app.services.rate_limiter import get_upload_rate_limiter


@pytest.fixture(autouse=True)
def _fresh_rate_limiter() -> Iterator[None]:
    """get_upload_rate_limiter() is @lru_cache'd (same singleton pattern as
    get_job_service()), so without this the same RateLimiter instance -- and
    its accumulated hit history -- would persist across the entire test
    session. Every test starting with a clean limiter keeps rate limiting
    from leaking between unrelated tests, the same way each test's own
    app.dependency_overrides keep job state from leaking. The default
    rate_limit_max_requests (20/min) comfortably covers any single test's
    normal request count; test_rate_limit_api.py deliberately overrides the
    limiter itself with a tiny one to prove the 429 path deterministically.
    """
    get_upload_rate_limiter.cache_clear()
    yield
