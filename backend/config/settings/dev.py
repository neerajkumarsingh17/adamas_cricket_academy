from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "192.168.1.66"]

# Dev/demo convenience only — deliberately not read in base.py, so
# staging.py/prod.py have no way to pick it up even by accident. When set,
# apps.iam.services.generate_and_store_otp issues this code for every
# mobile number instead of a random one, so anyone testing multiple
# accounts (admin/parent/student) doesn't need to fish the real code out
# of the console log each time.
DEV_STATIC_OTP = env("DEV_STATIC_OTP", default=None)  # noqa: F405

# LOCAL-SETUP.md: MinIO stands in for S3 in native dev by default. Set
# AWS_S3_ENDPOINT_URL="" (present, blank — not merely absent) in .env to
# opt out and talk to real S3 instead, e.g. when developing against a
# shared bucket rather than local MinIO.
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://localhost:9000")  # noqa: F405

# Namespaces this environment's uploads within the shared bucket — see
# AWS_S3_KEY_PREFIX's definition in base.py.
AWS_S3_KEY_PREFIX = env("AWS_S3_KEY_PREFIX", default="dev")  # noqa: F405
