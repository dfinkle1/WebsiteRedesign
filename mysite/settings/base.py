from pathlib import Path
import os
import environ
from dotenv import load_dotenv
import dj_database_url
from debug_toolbar.settings import PANELS_DEFAULTS


# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="unsafe-secret-key")
DEBUG = False  # Overridden in dev/prod

INSTALLED_APPS = [
    # Project apps
    "mysite",
    "apps.reimbursements.apps.ReimbursementsConfig",
    "apps.workshops.apps.WorkshopsConfig",
    "apps.frg.apps.FrgConfig",
    "apps.core.apps.CoreConfig",
    "apps.staff.apps.StaffConfig",
    "apps.news.apps.NewsConfig",
    "apps.events",
    # Django core
    "djangocms_admin_style",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "cms",
    "menus",
    # Utilities
    "django_recaptcha",
    "whitenoise.runserver_nostatic",
    "treebeard",
    "storages",
    "sekizai",
    "adminsortable2",
    "easy_thumbnails",
    # django CMS core
    # django CMS addons
    "djangocms_frontend",
    "djangocms_text.contrib.text_ckeditor4",
    "djangocms_frontend.contrib.accordion",
    "djangocms_frontend.contrib.alert",
    "djangocms_frontend.contrib.badge",
    "djangocms_frontend.contrib.card",
    "djangocms_frontend.contrib.carousel",
    "djangocms_frontend.contrib.collapse",
    "djangocms_frontend.contrib.content",
    "djangocms_frontend.contrib.grid",
    "djangocms_frontend.contrib.image",
    "djangocms_frontend.contrib.jumbotron",
    "djangocms_frontend.contrib.link",
    "djangocms_frontend.contrib.listgroup",
    "djangocms_frontend.contrib.media",
    "djangocms_frontend.contrib.tabs",
    "djangocms_frontend.contrib.utilities",
    "djangocms_text",
    "djangocms_link",
    "djangocms_versioning",
    "djangocms_alias",
    "djangocms_picture",
    "djangocms_file",
    "djangocms_video",
    "djangocms_googlemap",
    "djangocms_snippet",
    "djangocms_style",
    # Filer
    "filer",
]

# TEXT_EDITOR = "djangocms_text.contrib.text_ckeditor4.ckeditor4"
DEBUG_TOOLBAR_PANELS = [p for p in PANELS_DEFAULTS if "profiling" not in p]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]

ROOT_URLCONF = "mysite.urls"
WSGI_APPLICATION = "mysite.wsgi.application"


# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.i18n",
                "sekizai.context_processors.sekizai",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "cms.context_processors.cms_settings",
            ],
        },
    },
]

# CMS Settings
CMS_CONFIRM_VERSION4 = True
DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True


# TEXT_INLINE_EDITING = True
# TEXT_ADDITIONAL_TAGS = ("iframe",)
# TEXT_ADDITIONAL_ATTRIBUTES = (
#     "scrolling",
#     "allowfullscreen",
#     "frameborder",
#     "src",
#     "height",
#     "width",
# )

CMS_TEMPLATES = [
    ("cms_templates/home.html", "Home"),
    ("cms_templates/about.html", "About"),
    ("cms_templates/focused-landing.html", "Focused Collaborative Research"),
    ("cms_templates/joyfulmathematics.html", "Joyful Mathematics Template"),
    ("cms_templates/visiting.html", "Visiting Template"),
    ("cms_templates/resources.html", "Resources Template"),
    ("cms_templates/news.html", "News Template"),
    ("FRG/frg-resources.html", "FRG Resources"),
    ("FRG/frg-activities.html", "FRG Activities"),
    ("FRG/frg-landing.html", "FRG Landing Page"),
    ("FRG/frg-papers.html", "FRG Papers"),
    ("new_page_template.html", "New Page Template"),
    ("donate.html", "Donation Page"),
]

# Internationalization
LANGUAGE_CODE = "en"
LANGUAGES = [("en", "English"), ("de", "German"), ("it", "Italian")]
TIME_ZONE = "America/Vancouver"
USE_I18N = False
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Caching
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}
CMS_CACHE_DURATIONS = {"content": 3600, "menus": 3600, "permissions": 3600}

# Static and Media (Base Defaults)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATICFILES_DIRS = [BASE_DIR / "assets"]

# Site ID
SITE_ID = 2

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql",
#         "NAME": "<rds-db-name>",
#         "USER": "<rds-username>",
#         "PASSWORD": "<rds-password>",
#         "HOST": "<rds-endpoint>",
#         "PORT": "5432",
#     }
# }
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"), conn_max_age=600
    )
}


RECAPTCHA_PUBLIC_KEY = os.getenv("RECAPTCHA_PUBLIC_KEY")
RECAPTCHA_PRIVATE_KEY = os.getenv("RECAPTCHA_PRIVATE_KEY")


# Static & Media with S3
USE_S3 = env.bool("USE_S3", default=True)

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_S3_CUSTOM_DOMAIN = "dk87yvhh7cphv.cloudfront.net"

    AWS_CLOUDFRONT_DOMAIN = f"{AWS_S3_CUSTOM_DOMAIN}"
    AWS_LOCATION = "media"  # Keep for django-filer and legacy code

    # media
    AWS_MEDIA_BUCKET_NAME = os.getenv("AWS_MEDIA_BUCKET_NAME")
    AWS_PRIVATE_DOMAIN = f"{AWS_MEDIA_BUCKET_NAME}.s3.amazonaws.com"

    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_MEDIA_BUCKET_NAME,
                "querystring_auth": True,
                "default_acl": None,
                "querystring_expire": 300,
                "custom_domain": AWS_PRIVATE_DOMAIN,
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": "static",
                "custom_domain": "dk87yvhh7cphv.cloudfront.net",
            },
        },
    }

    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    # MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
