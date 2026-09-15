from .staging import *  # noqa: F403

# TEMPORARY bridge state for a fresh EC2 box that has no domain/TLS
# terminator in front of it yet (deploy/ guide, "get it running on the IP
# first"). staging.py's SECURE_SSL_REDIRECT/*_COOKIE_SECURE assume HTTPS —
# left on, every request 301s to an https:// origin that doesn't exist and
# the browser drops the Secure-flagged session/CSRF cookies, so the site
# never loads at all over plain HTTP.
#
# This is not a weaker *security policy* so much as it's honest about what
# the box currently has in front of it (no TLS). It carries real risk
# (JWT/OTP traffic in cleartext) for anything beyond a first smoke test —
# switch DJANGO_SETTINGS_MODULE back to config.settings.staging or .prod as
# soon as a domain + certbot cert are in place, per the deploy guide's HTTPS
# step, rather than leaving this as the permanent setting.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
