from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
