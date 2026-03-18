from .base import *
import os


DEBUG = False

# Error notification recipients
ADMINS = [("AIM Dev", env("ADMIN_EMAIL", default=""))]
MANAGERS = ADMINS

# Email — configure SMTP in .env for error emails and future notifications
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@aimath.org")
SERVER_EMAIL = env("SERVER_EMAIL", default="server@aimath.org")

# Production logging
# Apache/mod_wsgi captures stderr → Apache error log automatically.
# Set DJANGO_LOG_FILE in .env to also write to a rotating file (recommended).
_log_formatter = {
    "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}
_log_handlers = {
    "console": {
        "level": "WARNING",
        "class": "logging.StreamHandler",
        "formatter": "standard",
    },
}
_log_file = env("DJANGO_LOG_FILE", default="")
if _log_file:
    _log_handlers["file"] = {
        "level": "WARNING",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": _log_file,
        "maxBytes": 1024 * 1024 * 10,  # 10 MB
        "backupCount": 10,
        "formatter": "standard",
        "delay": True,
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": _log_formatter},
    "handlers": _log_handlers,
    "loggers": {
        "django": {
            "handlers": list(_log_handlers.keys()),
            "level": "WARNING",
            "propagate": True,
        },
        "django.request": {
            "handlers": list(_log_handlers.keys()),
            "level": "ERROR",
            "propagate": False,
        },
        "apps": {
            "handlers": list(_log_handlers.keys()),
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# CORS — restrict to production domains
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Content Security Policy (Django 6.0 native — no django-csp package needed)
# ---------------------------------------------------------------------------
# Middleware is added here rather than base.py so CSP is only enforced in prod.
# In dev, violations are not blocked — use SECURE_CSP_REPORT_ONLY in dev.py
# to test without breaking anything.
MIDDLEWARE = MIDDLEWARE + ["django.middleware.csp.ContentSecurityPolicyMiddleware"]

from django.utils.csp import CSP

SECURE_CSP = {
    # Default: only load resources from our own domain
    "default-src": [CSP.SELF],

    # Scripts: self + Bootstrap CDN
    # unsafe-inline required for Django CMS toolbar inline scripts
    "script-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://cdn.jsdelivr.net"],

    # Styles: self + Google Fonts + Bootstrap CDN
    # unsafe-inline required for Django CMS toolbar (writes inline style= attributes dynamically)
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE, "https://fonts.googleapis.com", "https://cdn.jsdelivr.net"],

    # Fonts: self + Google Fonts file server
    "font-src": [CSP.SELF, "https://fonts.gstatic.com", "https://cdn.jsdelivr.net"],

    # Images: self + data URIs (Bootstrap icons, CMS image widgets)
    "img-src": [CSP.SELF, "data:", "https:"],

    # Iframes from YouTube (djangocms-video embeds)
    "frame-src": [CSP.SELF, "https://www.youtube.com", "http://www.youtube.com", "https://www.youtube-nocookie.com"],

    # Connect (fetch/XHR): self + ORCID for OAuth
    "connect-src": [CSP.SELF, "https://orcid.org"],

    # Forms: only submit to self
    "form-action": [CSP.SELF],

    # Iframes: same origin only (Django CMS toolbar uses iframes)
    "frame-ancestors": [CSP.SELF],

    # No plugins
    "object-src": [CSP.NONE],

    # No base tag hijacking
    "base-uri": [CSP.SELF],
}

USE_S3 = True

ALLOWED_HOSTS = [
    "aimath.org",
    "www.aimath.org",
    "dev.aimath.org",
]

INSTALLED_APPS += [
    "whitenoise.runserver_nostatic",
]

# Static and Media (Base Defaults)
STATIC_URL = "/static/"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"), conn_max_age=600
    )
}

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["dev.aimath.org"])


# Security
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "SAMEORIGIN"  # Allow iframes from same origin (needed for django-cms toolbar)

# Additional security headers
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing

# URL handling
APPEND_SLASH = True  # Redirect /about to /about/ automatically
