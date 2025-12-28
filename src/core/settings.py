from pathlib import Path

import dj_database_url
import environ
import structlog

env = environ.Env()

BASE_DIR = Path(__file__).resolve().parent.parent

SERVICE_NAME = env(
    "SERVICE_NAME",
    default="pricewatch-api",
)
APP_ENV = env(
    "APP_ENV",
    default="development",
)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-j4m2ch4ezi60*i-4gz(hni^lqnip%7uq@p)l%7wcvi$fbzg2cp",
)
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool(
    "DJANGO_DEBUG",
    default=False,
)
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["*"],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third Party
    "django_structlog",
    "django_dramatiq",
    # Apps
    "src.tracker",
]

MIDDLEWARE = [
    "django_structlog.middlewares.RequestMiddleware",
    "src.tracker.middleware.TraceHeaderMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "src.core.urls"

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

WSGI_APPLICATION = "src.core.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default="postgres://user:password@postgres:5432/pricewatch_db",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

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
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env(
            "REDIS_URL",
            default="redis://redis:6379/0",
        ),
        "KEY_PREFIX": SERVICE_NAME,
    }
}

DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.rabbitmq.RabbitmqBroker",
    "OPTIONS": {
        "url": env(
            "RABBITMQ_URL",
            default="amqp://guest:guest@rabbitmq:5672/",
        ),
    },
    "MIDDLEWARE": [
        # "dramatiq.middleware.Prometheus", FIXME: Prometheus middleware is not working
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Callbacks",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "src.tracker.dramatiq_telemetry.DramatiqWorkerTelemetry",
    ],
}

DRAMATIQ_AUTODISCOVER_MODULES = ["tasks"]

LOG_JSON = env.bool("LOG_JSON", default=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structlog": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer()
            if LOG_JSON
            else structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structlog",
        },
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "pika": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
