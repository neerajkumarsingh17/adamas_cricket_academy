from datetime import timedelta
from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # pg_trgm/unaccent lookups for people.services.resolve_person() fuzzy matching.
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
]

AUTH_USER_MODEL = "iam.User"

LOCAL_APPS = [
    "apps.core",
    "apps.iam",
    "apps.audit",
    "apps.people",
    "apps.admissions.enquiry",
    "apps.admissions.trial",
    "apps.admissions.admission",
    "apps.admissions.student",
    "apps.admissions.parent",
    "apps.admissions.document",
    "apps.admissions.idcard",
    "apps.academics.batch",
    "apps.academics.attendance",
    "apps.finance.fee",
    "apps.finance.payment",
    "apps.engagement.communication",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "apps.core.middleware.RequestIDMiddleware",
    "apps.audit.middleware.CurrentRequestMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# docs/06-conventions.md: timezone is Asia/Kolkata, store UTC, render IST.
LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REDIS_URL = env("REDIS_URL")
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

# The first periodic task in this codebase — keeps TrainingSession rows
# generated ~4 weeks ahead of every active batch's weekly schedule
# (apps.academics.batch.services.generate_sessions) without anyone having
# to remember to run the management command by hand.
CELERY_BEAT_SCHEDULE = {
    "generate-training-sessions-weekly": {
        "task": "batch.generate_sessions",
        "schedule": crontab(day_of_week=0, hour=2, minute=0),
    },
}

# docs/07-storage.md: AWS_S3_ENDPOINT_URL points at local MinIO in dev only and is
# unset in staging/production, so boto3 talks to real S3. No code branches on it.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ap-south-1")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_EXPIRE = 300
AWS_S3_FILE_OVERWRITE = False
AWS_S3_SIGNATURE_VERSION = "s3v4"

# docs/07-storage.md assumes one bucket per environment
# (aca-oms-{dev|staging|prod}); this project instead shares one real
# bucket across environments, so every S3 key apps.admissions.document
# generates is namespaced under this prefix instead — same isolation,
# folder-based rather than bucket-based. Blank by default (nothing to
# namespace against once an environment has its own bucket);
# config/settings/dev.py sets its own default for the shared-bucket case.
AWS_S3_KEY_PREFIX = env("AWS_S3_KEY_PREFIX", default="")

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

NOTIFICATION_BACKEND = env("NOTIFICATION_BACKEND", default="console")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultCursorPagination",
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        # docs/02-api-spec.md: "public, rate-limited, captcha" for the
        # website enquiry widget. No rate is specified in the docs —
        # 10/hour per IP is a conservative starting point against scripted
        # abuse, tunable without a code change once real traffic is seen.
        "public_enquiry": "10/hour",
    },
}

SIMPLE_JWT = {
    # "Short-lived access, rotating refresh, old refresh blacklisted on
    # use" — docs/02-api-spec.md, Auth section.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    # last_login_at (docs/01-data-model.md section 1) is updated explicitly
    # in apps.iam views instead, since OTP login doesn't go through
    # simplejwt's own TokenObtainPairView at all.
    "UPDATE_LAST_LOGIN": False,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ACA-OMS API",
    "DESCRIPTION": "Adamas Cricket Academy Operations & Athlete Management System",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": True,
    # drf-spectacular names an enum from the field's owning model+field
    # name, not the Python choices-class name — apps.finance.payment.
    # Payment.status and apps.admissions.trial.TrialRegistration.
    # payment_status both auto-name to "PaymentStatusEnum" despite having
    # completely different values (confirmed/settled/void vs
    # not_applicable/pending/paid/waived), silently mismapping one of them
    # in the generated frontend types. Keyed by a hash of the actual
    # choice values, not the name, so this only affects this one enum.
    "ENUM_NAME_OVERRIDES": {
        "PaymentLedgerStatusEnum": "apps.finance.payment.models.PaymentLedgerStatus",
        # Same problem: AttendanceCorrection.status auto-names to a
        # collision hash ("StatusE94Enum") because three other models also
        # have a `status` field. The values were correct, but a hash suffix
        # changes whenever another status enum is added anywhere, breaking
        # every frontend reference to it — a stable name doesn't.
        "CorrectionStatusEnum": "apps.academics.attendance.models.CorrectionStatus",
    },
}
