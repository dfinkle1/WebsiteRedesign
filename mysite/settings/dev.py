from .base import *

DEBUG = True
USE_S3 = False

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "assets"]
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]

INSTALLED_APPS += ["django_browser_reload"]
MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]

DATABASE_URL = os.getenv("DATABASE_URL")  # e.g., from Codespaces secrets

DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=0)}

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "127.0.0.1:80000", "*"]

INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
