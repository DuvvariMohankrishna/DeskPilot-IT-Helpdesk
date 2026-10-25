import os
from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv


# ==================================================
# BASE DIRECTORY AND ENVIRONMENT VARIABLES
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env", override=False)


# ==================================================
# SECURITY AND DEBUG
# ==================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-only-change-this-secret-key",
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"

ALLOW_PUBLIC_REGISTRATION = (
    os.getenv("ALLOW_PUBLIC_REGISTRATION", "False").lower() == "true"
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS",
        "127.0.0.1,localhost",
    ).split(",")
    if host.strip()
]

if not DEBUG:
    if (
        not SECRET_KEY
        or SECRET_KEY == "dev-only-change-this-secret-key"
    ):
        raise RuntimeError(
            "Set a strong SECRET_KEY environment variable."
        )

    if not ALLOWED_HOSTS:
        raise RuntimeError(
            "Configure ALLOWED_HOSTS for production."
        )


# ==================================================
# INSTALLED APPLICATIONS
# ==================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    "django_filters",

    "core",
]


# ==================================================
# MIDDLEWARE
# ==================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    MIDDLEWARE.insert(
        1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )


# ==================================================
# URLS AND WSGI
# ==================================================

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"


# ==================================================
# TEMPLATES
# ==================================================

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


# ==================================================
# DATABASE: MYSQL / AIVEN
# ==================================================

DB_OPTIONS = {
    "charset": "utf8mb4",
}

DB_SSL_CA = os.getenv("DB_SSL_CA", "").strip()

if DB_SSL_CA:
    ca_path = Path(DB_SSL_CA)

    if not ca_path.is_absolute():
        ca_path = BASE_DIR / ca_path

    if not ca_path.is_file():
        raise RuntimeError(
            f"Database CA certificate not found: {ca_path}"
        )

    DB_OPTIONS["ssl"] = {
        "ca": str(ca_path),
    }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "it_helpdesk"),
        "USER": os.getenv("DB_USER", "root"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": DB_OPTIONS,
        "CONN_MAX_AGE": 60,
    }
}

if not DEBUG:
    required_db_variables = (
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
    )

    for variable in required_db_variables:
        if not os.getenv(variable):
            raise RuntimeError(
                f"Missing production environment variable: {variable}"
            )

    if not DB_SSL_CA:
        raise RuntimeError(
            "Set DB_SSL_CA to the Aiven CA certificate path."
        )


# ==================================================
# PASSWORD VALIDATION
# ==================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==================================================
# CUSTOM USER MODEL
# ==================================================

AUTH_USER_MODEL = "core.User"


# ==================================================
# INTERNATIONALIZATION
# ==================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"

USE_I18N = True
USE_TZ = True


# ==================================================
# STATIC AND MEDIA FILES
# ==================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": (
                "django.core.files.storage.FileSystemStorage"
            ),
        },
        "staticfiles": {
            "BACKEND": (
                "whitenoise.storage.CompressedManifestStaticFilesStorage"
            ),
        },
    }


# ==================================================
# DEFAULT PRIMARY KEY
# ==================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==================================================
# CORS: REACT / VITE
# ==================================================

CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173",
    ).split(",")
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = False


# ==================================================
# DJANGO REST FRAMEWORK
# ==================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": (
        "drf_spectacular.openapi.AutoSchema"
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 10,
}


# ==================================================
# JWT AUTHENTICATION
# ==================================================

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ==================================================
# API DOCUMENTATION
# ==================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "IT Helpdesk & Asset Management API",
    "DESCRIPTION": (
        "REST API for internal IT support and asset inventory."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# ==================================================
# PRODUCTION SECURITY
# ==================================================

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )

    SECURE_SSL_REDIRECT = (
        os.getenv("SECURE_SSL_REDIRECT", "True").lower() == "true"
    )

    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    CSRF_TRUSTED_ORIGINS = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CSRF_TRUSTED_ORIGINS",
            "",
        ).split(",")
        if origin.strip()
    ]

    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "same-origin"


# ==================================================
# LOGGING
# ==================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
        },
    },
}