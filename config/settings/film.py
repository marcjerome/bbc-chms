"""Settings for recording the pitch video: separate demo database, framable pages, stage files."""
from .dev import *  # noqa: F401,F403
from .dev import BASE_DIR

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "video" / "film.sqlite3"}}
X_FRAME_OPTIONS = "SAMEORIGIN"  # the stage pages put the app in iframes (split screen, phone frame)
STATICFILES_DIRS = [BASE_DIR / "static", ("film", BASE_DIR / "video" / "stage")]
