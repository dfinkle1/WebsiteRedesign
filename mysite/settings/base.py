from dotenv import load_dotenv
from pathlib import Path
import environ
import dj_database_url
import os


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASE_URL = os.getenv("DATABASE_URL")


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv("SECRET_KEY"))

# SECURITY WARNING: don't run with debug turned on in production!


env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, ".env"))
# Application definition

INSTALLED_APPS = [
    "mysite",
    "participants.apps.ParticipantsConfig",
    "apps.workshops.apps.WorkshopsConfig",
    "apps.frg.apps.FrgConfig",
    "apps.core.apps.CoreConfig",
    "djangocms_admin_style",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "cms",
    "menus",
    "django.contrib.sites",
    "treebeard",
    "djangocms_versioning",
    "djangocms_alias",
    "sekizai",
    "filer",
    "easy_thumbnails",
    "djangocms_text_ckeditor",
    "djangocms_picture",
    "djangocms_file",
    "djangocms_video",
    "djangocms_googlemap",
    "djangocms_snippet",
    "djangocms_style",
    "storages",
    "adminsortable2",
]

##django pictures##
DJANGOCMS_PICTURE_ALIGN = [
    ("left", ("Align left")),
    ("start", ("Float left")),
    ("end", ("Float right")),
]
##
THUMBNAIL_HIGH_RESOLUTION = True

THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    "filer.thumbnail_processors.scale_and_crop_with_subject_location",
    "easy_thumbnails.processors.filters",
)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",  # not installed by default
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
]


# STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

TEXT_INLINE_EDITING = True

X_FRAME_OPTIONS = "SAMEORIGIN"

ROOT_URLCONF = "mysite.urls"


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
                "cms.context_processors.cms_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "mysite.wsgi.application"

CSRF_TRUSTED_ORIGINS = ["https://websiteredesign-production.up.railway.app"]
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
TEXT_ADDITIONAL_TAGS = ("iframe",)
TEXT_ADDITIONAL_ATTRIBUTES = (
    "scrolling",
    "allowfullscreen",
    "frameborder",
    "src",
    "height",
    "width",
)


DATABASES = {"default": dj_database_url.config(default=DATABASE_URL, conn_max_age=600)}

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/


LANGUAGES = [("en", "English"), ("de", "German"), ("it", "Italian")]
LANGUAGE_CODE = "en"

TIME_ZONE = "America/Vancouver"


USE_TZ = True


##### DJANGO CMS #######

CMS_CONFIRM_VERSION4 = True
USE_I18N = False
DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

SITE_ID = 2
FILER_ENABLE_PERMISSIONS = True
FILER_ENABLE_SUBDIRECTORIES = True

CMS_TEMPLATES = [
    ("template1.html", "Basic Template"),
    ("FRG/frg-resources.html", "frg resources"),
    ("FRG/frg-activities.html", "frg activities"),
    ("testtemplate.html", "customcms"),
    ("home.html", "home"),
    ("about.html", "about"),
    ("focused-landing.html", "focused collaborative research"),
    ("joyfulmathematics.html", "joyful mathematics template"),
    ("visiting.html", "visiting template"),
    ("resources.html", "resources template"),
    ("news.html", "news template"),
    ("staff_member_plugin.html", "update staff template"),
    ("FRG/frg-landing.html", "frg landing page"),
    ("FRG/frg-papers.html", "frg papers"),
    ("new_page_template.html", "new_page_template"),
]

###########

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/


# last working build mar 20th
# STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# STATIC_URL = "static/"
# STATICFILES_DIRS = [
#     BASE_DIR / "static",
# ]


USE_S3 = os.getenv("USE_S3") == "TRUE"

if USE_S3:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_DEFAULT_ACL = "public-read"
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_S3_CUSTOM_DOMAIN = "dk87yvhh7cphv.cloudfront.net"
    AWS_CLOUDFRONT_DOMAIN = f"{AWS_S3_CUSTOM_DOMAIN}"

    AWS_LOCATION = "static"

    STORAGES = {
        "default": {
            "BACKEND": "utils.storages_backends.MediaStorage",  # Your custom media storage
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "custom_domain": AWS_CLOUDFRONT_DOMAIN,
                # add other boto3 options you use here
            },
        },
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "bucket_name": AWS_STORAGE_BUCKET_NAME,
                "location": AWS_LOCATION,
                "custom_domain": AWS_CLOUDFRONT_DOMAIN,
                # other options like ACL or CacheControl can be added here
            },
        },
    }

    STATIC_URL = f"{AWS_CLOUDFRONT_DOMAIN}/{AWS_LOCATION}/"
    MEDIA_URL = f"{AWS_CLOUDFRONT_DOMAIN}/media/"
else:
    STATIC_URL = "/static/"
    STATIC_ROOT = os.path.join(BASE_DIR, "static")
    MEDIA_URL = "/media/"
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")


# MEDIA_URL = "/media/"
# MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# Ensure static files directory is detected
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, "static"),
# ]


# USE_S3 = os.getenv('USE_S3') == 'TRUE'

# if USE_S3:
#     # aws settings
#     AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
#     AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
#     AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
#     AWS_DEFAULT_ACL = 'public-read'
#     AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
#     AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
#     # s3 static settings
#     AWS_LOCATION = 'static'
#     STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'
#     STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# else:
#     STATIC_URL = '/static/'
#     STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
