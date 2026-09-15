import pytest
import redis
from django.conf import settings


@pytest.fixture(autouse=True)
def _clear_otp_redis_keys():
    """OTP state lives in Redis, not the DB — pytest-django's transaction
    rollback between tests doesn't touch it, so tests would otherwise leak
    rate-limit counters into each other.
    """
    client = redis.from_url(settings.REDIS_URL)
    for key in client.scan_iter("otp:*"):
        client.delete(key)
    yield
    for key in client.scan_iter("otp:*"):
        client.delete(key)
