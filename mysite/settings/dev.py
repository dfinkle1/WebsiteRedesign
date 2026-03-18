from .base import *

DEBUG = os.getenv("DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

INSTALLED_APPS += ["debug_toolbar"]
CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:8000", "http://localhost:8000"]
INTERNAL_IPS = ["127.0.0.1"]

# Debug toolbar middleware — dev only, kept out of base.py
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE

# -- static/media
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "assets"]
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


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

# CSP in report-only mode for dev — violations appear in browser console, nothing is blocked
MIDDLEWARE = MIDDLEWARE + ["django.middleware.csp.ContentSecurityPolicyMiddleware"]

from django.utils.csp import CSP

SECURE_CSP_REPORT_ONLY = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://cdn.jsdelivr.net"],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],
    "font-src": [CSP.SELF, "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],
    "img-src": [CSP.SELF, "data:", "https:"],
    "frame-src": [CSP.SELF, "https://www.youtube.com", "http://www.youtube.com", "https://www.youtube-nocookie.com"],
    "connect-src": [CSP.SELF, "https://orcid.org"],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
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
