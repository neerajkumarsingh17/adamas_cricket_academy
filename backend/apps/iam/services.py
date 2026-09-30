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

from apps.people.services import normalize_mobile_e164

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


def _test_otp(mobile: str) -> str | None:
    """settings.OTP_TEST_NUMBERS ("mobile:code,mobile:code", .env-configured,
    blank by default): a fixed code for specific test numbers only — every
    other number still gets a random one, in every environment including
    staging/prod. `mobile` is already E.164-normalised (this module's own
    contract); test numbers are normalised the same way here so `.env` can
    list them in whatever raw form is convenient.
    """
    raw = getattr(settings, "OTP_TEST_NUMBERS", "") or ""
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        raw_mobile, _, code = pair.partition(":")
        try:
            if normalize_mobile_e164(raw_mobile.strip()) == mobile:
                return code.strip()
        except ValueError:
            continue
    return None


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

    # Two fixed-code overrides, checked before falling back to random:
    #  1. OTP_TEST_NUMBERS (base.py) — specific numbers only, every
    #     environment including staging/prod. Logged below since it's a
    #     deliberate exception on a real deployment.
    #  2. DEV_STATIC_OTP (dev.py only, unset in staging.py/prod.py) — every
    #     number, so testing several demo accounts locally doesn't mean
    #     fishing the real code out of the console log each time.
    # Either way the code is still stored and rate-limited exactly like a
    # random one — only where the code itself comes from changes.
    test_otp = _test_otp(mobile)
    if test_otp:
        logger.warning("TEST OTP override used for %s (fixed code, not random).", mobile)
    static_otp = getattr(settings, "DEV_STATIC_OTP", None)
    otp = test_otp or static_otp or f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"
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
