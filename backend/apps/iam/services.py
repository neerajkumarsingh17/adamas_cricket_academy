"""OTP generation/verification (docs/02-api-spec.md, Auth section) and a
stubbed SMS "backend" for delivering it. The real multi-channel
notification service (NotificationTemplate, NotificationLog, provider
adapters) is apps.core's later job (T-204) — this is scoped to OTP
delivery only, and only implements the console backend.

Callers pass an already E.164-normalised mobile number.
"""

import hashlib
import logging
import secrets

import redis
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_TTL_SECONDS = 600  # 10 minutes
OTP_RATE_LIMIT = 3
OTP_RATE_WINDOW_SECONDS = 600  # 10 minutes


def _redis_client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


def _otp_key(mobile: str) -> str:
    return f"otp:code:{mobile}"


def _rate_key(mobile: str) -> str:
    return f"otp:rate:{mobile}"


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_and_store_otp(mobile: str) -> str:
    """Rate-limited to OTP_RATE_LIMIT requests per OTP_RATE_WINDOW_SECONDS
    per mobile — raises rest_framework.exceptions.Throttled past that.

    Only the hash is stored, in Redis with a TTL, never the plaintext code
    and never in the database at all.
    """
    client = _redis_client()
    rate_key = _rate_key(mobile)
    count = client.incr(rate_key)
    if count == 1:
        client.expire(rate_key, OTP_RATE_WINDOW_SECONDS)
    if count > OTP_RATE_LIMIT:
        wait = client.ttl(rate_key)
        raise Throttled(wait=wait if wait and wait > 0 else OTP_RATE_WINDOW_SECONDS)

    # Dev/demo convenience (config/settings/dev.py's DEV_STATIC_OTP,
    # unset in staging.py/prod.py): every mobile number gets the same
    # fixed code instead of a random one, so testing several accounts
    # (admin/parent/student) doesn't mean fishing the real code out of the
    # console log each time. Still stored and rate-limited exactly like a
    # random code — only where the code itself comes from changes.
    static_otp = getattr(settings, "DEV_STATIC_OTP", None)
    otp = static_otp or f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"
    client.set(_otp_key(mobile), _hash_otp(otp), ex=OTP_TTL_SECONDS)
    return otp


def verify_otp(mobile: str, otp: str) -> bool:
    """One-time use: a verified (or exhausted) code can't be replayed."""
    client = _redis_client()
    key = _otp_key(mobile)
    stored_hash = client.get(key)
    if stored_hash is None:
        return False
    stored_hash_str = stored_hash.decode() if isinstance(stored_hash, bytes) else stored_hash
    if stored_hash_str != _hash_otp(otp):
        return False
    client.delete(key)
    return True


def get_or_create_user_for_person(person, *, role_code: str) -> tuple:
    """Provisions the OTP login a Guardian or Student needs to use the
    existing role-agnostic `OTPVerifyView` (docs/02-api-spec.md's Auth
    section) — that view has no separate "signup" step, so something has
    to create the `User` row the first time someone is given portal
    access. Shared by the guardian-mapping flow (role="parent") and the
    student login-access action (role="student") so the provisioning rule
    — including the collision guard below — only lives in one place.

    Returns `(user, created)`.
    """
    from .models import Role, User, UserRole

    user = User.objects.filter(person=person).first()
    created = False
    if user is None:
        # OTPVerifyView._find_user_by_mobile requires *exactly one* active
        # User per mobile number — a second Person sharing that number
        # (e.g. a family phone) would make login permanently ambiguous for
        # both. Caught here, at the one place a User first gets created
        # for a Person, rather than surfacing as an inexplicable login
        # failure later.
        if User.objects.filter(person__mobile=person.mobile, is_active=True).exists():
            raise ValidationError(
                {
                    "mobile": (
                        "This mobile number already has a login registered to a "
                        "different person. Use a distinct mobile number before "
                        "granting portal access."
                    )
                }
            )
        user = User.objects.create(login_id=person.mobile, person=person, is_active=True)
        user.set_unusable_password()
        user.save(update_fields=["password"])
        created = True

    role = Role.objects.get(code=role_code)
    UserRole.objects.get_or_create(
        user=user, role=role, defaults={"valid_from": timezone.localdate()}
    )
    return user, created


def send_otp_sms(mobile: str, otp: str) -> None:
    """Stubbed SMS backend — NOTIFICATION_BACKEND=console is the only one
    implemented here. Real provider adapters (MSG91 etc.) are apps.core's
    later notification service.
    """
    if settings.NOTIFICATION_BACKEND == "console":
        logger.info("OTP for %s: %s (console backend — dev/test only)", mobile, otp)
        return
    raise NotImplementedError(
        f"No SMS backend implemented for NOTIFICATION_BACKEND={settings.NOTIFICATION_BACKEND!r}"
    )
