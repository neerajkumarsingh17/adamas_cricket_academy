from .base import *  # noqa: F403

DEBUG = False

# Notifications are queued via Celery (docs/01-data-model.md section 4:
# "Dispatch is always async via Celery") — eager execution means tests can
# assert on the dispatched result without a running broker/worker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

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
