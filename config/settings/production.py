from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# On-premise: accept the church computer on any private network address (whatever the router gives it),
# so phones and tablets on the church Wi-Fi can reach it. Public addresses are still refused.
# Set PRIVATE_NETWORK_HOSTS=false to go back to the strict ALLOWED_HOSTS list.
if env.bool("PRIVATE_NETWORK_HOSTS", default=True):
    LISTED_HOSTS = ALLOWED_HOSTS  # noqa: F405 - extra names (e.g. a domain) still allowed
    ALLOWED_HOSTS = ["*"]
    MIDDLEWARE = ["core.middleware.PrivateNetworkHostMiddleware", *MIDDLEWARE]  # noqa: F405

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = env.bool("SECURE_COOKIES", default=False)
CSRF_COOKIE_SECURE = env.bool("SECURE_COOKIES", default=False)
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 hours: shared church-office machines

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
