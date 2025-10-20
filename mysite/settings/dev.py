from .base import *


INSTALLED_APPS += ["debug_toolbar"]
INTERNAL_IPS = [
    "127.0.0.1",
]

# -- static/media
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "assets"]
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

BLOCK_REMOTE_MEDIA = os.getenv("BLOCK_REMOTE_MEDIA", "1") == "1" and DEBUG

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

APP_ENV = os.getenv("APP_ENV", "local")


IN_CODESPACES = (
    os.getenv("GITHUB_CODESPACES") == "true"
    or os.getenv("CODESPACES") == "true"
    or bool(os.getenv("CODESPACE_NAME"))
)

# default debug: for local or codespaces
DEBUG = (
    os.getenv(
        "DEBUG",
        "1" if APP_ENV in {"local", "codespaces"} or IN_CODESPACES else "0",
    )
    == "1"
)


ALLOWED_HOSTS = ["localhost", "127.0.0.1", "127.0.0.1:80000", "*"]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

if APP_ENV == "codespaces" or IN_CODESPACES:
    ALLOWED_HOSTS += ["*githubpreview.dev"]
    CSRF_TRUSTED_ORIGINS += ["https://*.githubpreview.dev"]

DB_URL = None
if APP_ENV == "codespaces" or IN_CODESPACES:
    DB_URL = (
        os.getenv("DATABASE_URL_CODESPACES")
        or os.getenv("MOCK_DATABASE_URL")
        or os.getenv("DATABASE_URL")
    )
elif APP_ENV == "local":
    DB_URL = os.getenv("DATABASE_URL_LOCAL") or os.getenv("DATABASE_URL")

if DB_URL:
    DATABASES = {"default": dj_database_url.parse(DB_URL, conn_max_age=0)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": "aim_local",
            "USER": "daniel",
            "PASSWORD": "",
            "HOST": "localhost",
            "PORT": "5431",
        }
    }
