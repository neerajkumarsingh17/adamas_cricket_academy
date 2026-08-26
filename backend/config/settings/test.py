from .base import *  # noqa: F403

DEBUG = False

# LOCAL-SETUP.md: the test suite must not touch MinIO/S3 — it fails on
# someone else's machine otherwise. Presign calls are mocked in test code.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
