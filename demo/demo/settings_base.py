"""Settings shared by both demo flavours.

Never use these settings for anything but the demo: ``DEBUG`` is on, the
secret key is public and ``ALLOWED_HOSTS`` accepts everything.
"""

from pathlib import Path

# ``demo/demo/settings_base.py`` -> ``demo/``
BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = True

SECRET_KEY = "django-insecure-demo-key-do-not-use-anywhere-else"

# The demo is routinely driven by ``django.test.Client`` (host ``testserver``)
# and by curl against 127.0.0.1, so accept anything.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # The library under demonstration and its table renderer.
    "django_tables2",
    "flexible_reports",
    # The demo's own reportable domain.
    "demoapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "demo.urls"
WSGI_APPLICATION = "demo.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                # Required: ``{% flexible %}`` hands the parent template
                # context to the django-tables2 adapter, which needs
                # ``request`` in it.
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- demo-specific knobs -------------------------------------------------
#
# Slug of the report created by ``manage.py seed_demo`` and rendered by the
# home page, plus the value fed into the parametrised DjangoQL query.
DEMO_REPORT_SLUG = "library-report"
DEMO_MIN_PAGES = 300
