"""Django settings for Deskline Requester Ticket Inbox.

Everything a self-hoster needs is auto-detected: SQLite in the project root,
static files served by runserver, and a development SECRET_KEY fallback so a
fresh clone boots with no .env file at all.
"""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# A development-only fallback keeps `git clone && migrate && runserver` working
# with zero configuration. Production deployments set DJANGO_SECRET_KEY.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "cenius-dev-4b7d21e9c05f8a63")

# DEBUG stays on so runserver serves /static/ without collectstatic.
DEBUG = os.environ.get("DJANGO_DEBUG", "true").strip().lower() != "false"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "tickets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "tickets.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "deskline.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "tickets.context_processors.deskline_context",
            ],
        },
    },
]

WSGI_APPLICATION = "deskline.wsgi.application"


def _database_from_environment():
    """DATABASE_URL wins when it points at Postgres; SQLite is the default."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith(("postgres://", "postgresql://")):
        parsed = urlparse(url)
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": (parsed.path or "/deskline").lstrip("/") or "deskline",
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


DATABASES = {"default": _database_from_environment()}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Deskline's single default SLA window: every ticket promises a first response
# within this many hours of being raised. Overridable for self-hosters.
SLA_WINDOW_HOURS = int(os.environ.get("DESKLINE_SLA_HOURS", "8"))
SLA_DUE_SOON_HOURS = int(os.environ.get("DESKLINE_SLA_DUE_SOON_HOURS", "4"))

# Seed credentials documented in the README and printed on the sign-in card.
DEMO_AGENT_USERNAME = "cenius"
DEMO_AGENT_EMAIL = "cenius@cenius.ai"
DEMO_REQUESTER_USERNAME = "maya.chen"
DEMO_PASSWORD = "cenius"  # documented, preview-only demo credential

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Never enable SECURE_SSL_REDIRECT / secure cookies by default: Deskline is
# self-hosted on plain HTTP too, and a "secure" session cookie would be dropped.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
