from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# LOCAL-SETUP.md: MinIO stands in for S3 in native dev. This is the only
# setting that differs from staging/production.
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="http://localhost:9000")  # noqa: F405
