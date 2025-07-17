from pathlib import Path
import os
import environ
from dotenv import load_dotenv
import dj_database_url
from cms.utils.conf import get_cms_setting

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
    "participants.apps.ParticipantsConfig",
    "apps.workshops.apps.WorkshopsConfig",
    "apps.frg.apps.FrgConfig",
    "apps.core.apps.CoreConfig",
    "apps.staff.apps.StaffConfig",
    "apps.news.apps.NewsConfig",
    # Django core
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
    "whitenoise.runserver_nostatic",
    "treebeard",
    "storages",
    "sekizai",
    "adminsortable2",
    "easy_thumbnails",
    # django CMS core
    # django CMS addons
    "djangocms_text",
    "djangocms_link",
    "djangocms_admin_style",
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
    ("staff_member_plugin.html", "Staff Template"),
    ("new_page_template.html", "New Page Template"),
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

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL"), conn_max_age=600
    )
}

# Static & Media with S3
# USE_S3 = env.bool("USE_S3", default=True)

# if USE_S3:
#     AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
#     AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
#     AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
#     AWS_DEFAULT_ACL = "public-read"
#     AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
#     AWS_S3_CUSTOM_DOMAIN = "dk87yvhh7cphv.cloudfront.net"
#     AWS_CLOUDFRONT_DOMAIN = f"{AWS_S3_CUSTOM_DOMAIN}"
#     AWS_LOCATION = "static"

#     STORAGES = {
#         "default": {
#             "BACKEND": "utils.storages_backends.MediaStorage",
#             "OPTIONS": {
#                 "bucket_name": AWS_STORAGE_BUCKET_NAME,
#                 "custom_domain": AWS_S3_CUSTOM_DOMAIN,
#             },
#         },
#         "staticfiles": {
#             "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
#             "OPTIONS": {
#                 "bucket_name": AWS_STORAGE_BUCKET_NAME,
#                 "location": "static",
#                 "custom_domain": AWS_S3_CUSTOM_DOMAIN,
#             },
#         },
#     }

#     STATIC_URL = f"{AWS_CLOUDFRONT_DOMAIN}/{AWS_LOCATION}/"
#     MEDIA_URL = f"{AWS_CLOUDFRONT_DOMAIN}/media/"
