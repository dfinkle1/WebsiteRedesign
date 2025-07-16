from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ✅ S3 for Media ONLY
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

STORAGES = {
    # Media from S3
    "default": {
        "BACKEND": "utils.storages_backends.MediaStorage",
    },
    # Static local
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "assets"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ✅ Media via S3
MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
