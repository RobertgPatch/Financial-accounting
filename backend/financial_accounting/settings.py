import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-financial-accounting-dev-key-change-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

_allowed_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]

# Railway sets RAILWAY_PUBLIC_DOMAIN; auto-allow it so you don't have to
# duplicate the hostname in DJANGO_ALLOWED_HOSTS.
_railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN')
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'financial_accounting.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'financial_accounting.wsgi.application'

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
# Railway's Postgres plugin exposes individual PGXXX variables which are
# immune to URL-parsing issues (passwords with #, ?, @, etc.).  We prefer
# those.  Fall back to DATABASE_URL / DATABASE_PUBLIC_URL for local Docker
# Compose or other hosts that set the standard URL variable.
# ---------------------------------------------------------------------------
_pg_host = os.environ.get('PGHOST')
_pg_port = os.environ.get('PGPORT', '5432')
_pg_name = os.environ.get('PGDATABASE')
_pg_user = os.environ.get('PGUSER')
_pg_pass = os.environ.get('PGPASSWORD')

if _pg_host and _pg_name and _pg_user:
    # ---------- Railway (or any host providing individual PG vars) ----------
    _is_internal = _pg_host.endswith('.railway.internal')
    _options = {}
    if not DEBUG and not _is_internal:
        _options['sslmode'] = 'require'

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _pg_name,
            'USER': _pg_user,
            'PASSWORD': _pg_pass or '',
            'HOST': _pg_host,
            'PORT': _pg_port,
            'CONN_MAX_AGE': 600,
            'OPTIONS': _options,
        }
    }
else:
    # ---------- Fallback: DATABASE_URL (local Docker Compose, etc.) ---------
    if not os.environ.get('DATABASE_URL') and os.environ.get('DATABASE_PUBLIC_URL'):
        os.environ['DATABASE_URL'] = os.environ['DATABASE_PUBLIC_URL']

    DATABASES = {
        'default': dj_database_url.config(
            default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
            conn_max_age=600,
        )
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

_cors_origins = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://localhost:5173',
)
CORS_ALLOWED_ORIGINS = [o.strip().rstrip('/') for o in _cors_origins.split(',') if o.strip()]

# CSRF trusted origins – required when Railway proxies requests over HTTPS.
CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
if _railway_domain:
    CSRF_TRUSTED_ORIGINS.append(f'https://{_railway_domain}')

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}
