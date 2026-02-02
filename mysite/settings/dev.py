from .base import *


DEBUG = os.getenv("DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "*"]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS += ["debug_toolbar"]
INTERNAL_IPS = [
    "127.0.0.1",
]

# -- static/media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

BLOCK_REMOTE_MEDIA = os.getenv("BLOCK_REMOTE_MEDIA", "1") == "1" and DEBUG

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Database configuration
DB_URL = os.getenv("DATABASE_URL")

if DB_URL:
    DATABASES = {"default": dj_database_url.parse(DB_URL, conn_max_age=0)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "postgres"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "DEBUG"},
        "allauth": {"handlers": ["console"], "level": "DEBUG"},
        "allauth.socialaccount": {"handlers": ["console"], "level": "DEBUG"},
        "accounts": {"handlers": ["console"], "level": "DEBUG"},
    },
}
