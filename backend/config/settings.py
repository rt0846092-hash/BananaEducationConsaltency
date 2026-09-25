"""
Django settings for the Banana consultancy API.

Everything that differs between your laptop and Render is read from an
environment variable, so the code you run locally is the code that ships.
"""

import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# PyMySQL is a pure-Python MySQL driver. mysqlclient is faster but needs a C
# compiler, which makes deploys fail in confusing ways. This shim lets Django
# use PyMySQL wherever it expects MySQLdb.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:
    pass


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "insecure-dev-key-do-not-use-in-production")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

# Render gives every service a hostname in this variable. Adding it here means
# you never have to remember to update ALLOWED_HOSTS after deploying.
RENDER_HOST = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# One URL controls the database. mysql://... locally, postgres://... on Render.
DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
        conn_max_age=600,
    )
}

# MySQL's "utf8" is a 3-byte charset that silently mangles Korean, Nepali and
# Bengali characters. utf8mb4 is the real one. This is not optional.
if "mysql" in DATABASES["default"].get("ENGINE", ""):
    DATABASES["default"].setdefault("OPTIONS", {})["charset"] = "utf8mb4"

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kathmandu")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Student documents (passports, bank statements). Render wipes its disk on
# every deploy, so production must use object storage. Set the AWS_* variables
# for Amazon S3, or also AWS_S3_ENDPOINT_URL for Cloudflare R2 / Backblaze B2.
# Files are private and only ever downloaded through the API, which checks
# that the person asking is allowed to see that student.
MEDIA_ROOT = BASE_DIR / "media"
DOCUMENT_BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME", "")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if DOCUMENT_BUCKET:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": DOCUMENT_BUCKET,
            "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
            "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
            "region_name": os.getenv("AWS_S3_REGION_NAME") or None,
            "endpoint_url": os.getenv("AWS_S3_ENDPOINT_URL") or None,
            "default_acl": "private",
            "querystring_auth": True,
            "file_overwrite": False,
        },
    }

# True when uploaded documents survive a redeploy. The staff area warns the
# owner when they don't.
DOCUMENTS_PERSISTENT = bool(DOCUMENT_BUCKET) or DEBUG
MAX_DOCUMENT_MB = int(os.getenv("MAX_DOCUMENT_MB", "10"))
DATA_UPLOAD_MAX_MEMORY_SIZE = (MAX_DOCUMENT_MB + 1) * 1024 * 1024

# --- Office details used in emails -----------------------------------------
OFFICE_NAME = os.getenv("OFFICE_NAME", "Banana Education")
OFFICE_PHONE = os.getenv("OFFICE_PHONE", "01-555 1234")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
OFFICE_NOTIFY_EMAILS = env_list("OFFICE_NOTIFY_EMAILS")

# --- Email -----------------------------------------------------------------
# No EMAIL_HOST: messages are printed to the log instead of sent. For Gmail use
# smtp.gmail.com, port 587 and an app password, not the account password.
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
    EMAIL_TIMEOUT = 10
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", f"{OFFICE_NAME} <noreply@example.com>")

# --- New students from the website ------------------------------------------
# See core/assignment.py for the rule. False leaves them for the owner.
AUTO_ASSIGN = os.getenv("AUTO_ASSIGN", "True").lower() == "true"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "core.authentication.PasswordAwareJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
        "core.permissions.PasswordIsSet",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    # One limit cannot do two jobs. Reading public pages and submitting a form
    # need very different ceilings: a cyber cafe or a mobile carrier puts
    # hundreds of real students behind one IP address, so a tight global limit
    # takes the site down for exactly the people it is meant to serve.
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.AnonRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "600/hour",    # browsing — generous, it is only an abuse guard
        # Form submissions from one IP. An education fair puts dozens of
        # students on one Wi-Fi network; at 12/hour the thirteenth was turned
        # away for an hour. The honeypot and duplicate check handle spam.
        "intake": "120/hour",
        "login": "10/hour",    # brute force attempts
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# The React app runs on a different domain, so the browser blocks its requests
# unless that domain is listed here. This is the single most common reason a
# working local build fails after deploying.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# Django's own runserver cannot serve HTTPS at all, so redirecting to it there
# is always wrong. Without this guard, a missing .env silently turns on the
# production redirect and every local request dies in a loop the browser then
# caches. Deployment uses gunicorn, so this never applies on Render.
IS_DEV_SERVER = "runserver" in sys.argv

if not DEBUG and not IS_DEV_SERVER:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if o.startswith("https")]
    if RENDER_HOST:
        CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_HOST}")