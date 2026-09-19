"""Explicit demo/development/test/production configuration; PostgreSQL in all modes."""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[3]
ENVIRONMENT = os.getenv("PHILANTHRA_ENV", "development")
DEMO_MODE = ENVIRONMENT == "demo"
DEBUG = os.getenv("DEBUG", "0") == "1"
SECRET_KEY = os.getenv("SECRET_KEY", "local-development-only-change-before-deployment")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,api,testserver").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8080,http://127.0.0.1:8080,http://localhost:3000,http://127.0.0.1:3000",
).split(",")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://philanthra:philanthra-local@127.0.0.1:55432/philanthra_demo"
)
db = urlparse(DATABASE_URL)
if db.scheme not in ("postgres", "postgresql"):
    raise ImproperlyConfigured("PostgreSQL is required")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db.path.lstrip("/"),
        "USER": db.username,
        "PASSWORD": db.password,
        "HOST": db.hostname,
        "PORT": db.port or 5432,
        "CONN_MAX_AGE": 0,
        "OPTIONS": {"connect_timeout": 5},
    }
}
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "philanthra.core",
    "philanthra.demo",
    "philanthra.catalog",
    "philanthra.pilot",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.RequestMetadataMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / ".runtime/static"
MEDIA_ROOT = BASE_DIR / ".runtime/private-uploads"
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
CSRF_FAILURE_VIEW = "config.middleware.csrf_failure"
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
CSRF_COOKIE_SECURE = ENVIRONMENT == "production"
SESSION_COOKIE_AGE = 8 * 60 * 60
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = ENVIRONMENT == "production"
SECURE_HSTS_SECONDS = 31536000 if ENVIRONMENT == "production" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == "production"
SECURE_HSTS_PRELOAD = ENVIRONMENT == "production"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = BASE_DIR / ".runtime/mail"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "pilot@localhost")
PHILANTHRA_LLM_PROVIDER = os.getenv("PHILANTHRA_LLM_PROVIDER", "none")
PHILANTHRA_LLM_MODEL = os.getenv("PHILANTHRA_LLM_MODEL", "")
PHILANTHRA_DEMO_CLOCK = "2026-09-01T12:00:00Z"
REST_FRAMEWORK = {
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "300/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Philanthra Pilot API",
    "VERSION": "1.0.0",
    "DESCRIPTION": "Session-authenticated, permission-checked pilot API. Synthetic demo data is not real evidence.",
    "SERVE_INCLUDE_SCHEMA": False,
}
REST_FRAMEWORK["EXCEPTION_HANDLER"] = "philanthra.core.exceptions.exception_handler"
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
            ]
        },
    }
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "metadata"}},
    "formatters": {"metadata": {"()": "config.logging.MetadataFormatter"}},
    "loggers": {
        "philanthra.requests": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "philanthra.jobs": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
}

if ENVIRONMENT not in {"demo", "development", "test", "production"}:
    raise ImproperlyConfigured("Unknown PHILANTHRA_ENV")
if ENVIRONMENT == "production":
    if (
        not os.getenv("ALLOWED_HOSTS")
        or not ALLOWED_HOSTS
        or any(host in {"localhost", "127.0.0.1", "api", "testserver"} for host in ALLOWED_HOSTS)
    ):
        raise ImproperlyConfigured(
            "Production requires explicit deployment hostnames; development defaults are forbidden"
        )
    if DEBUG or len(SECRET_KEY) < 50 or "local-development" in SECRET_KEY or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            "Production requires debug off, a strong secret and explicit hosts"
        )
    if not os.getenv("DATABASE_URL") or any(
        x in DATABASE_URL for x in ("philanthra-local", "philanthra_demo")
    ):
        raise ImproperlyConfigured("Production requires dedicated database credentials")
    if os.getenv("DEMO_MODE", "0") != "0" or any(
        not x.startswith("https://") for x in CSRF_TRUSTED_ORIGINS
    ):
        raise ImproperlyConfigured("Production forbids demo shortcuts and insecure trusted origins")
    if not os.getenv("STORAGE_ENCRYPTION_ACK") == "configured":
        raise ImproperlyConfigured("Production storage encryption must be configured externally")
