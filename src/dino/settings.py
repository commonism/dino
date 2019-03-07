"""
Django settings for dino project.

Generated by 'django-admin startproject' using Django 2.1.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
import sys

import dj_database_url
from dino.common.config import Config

env_files = [
    '/etc/dino.cfg',
    os.path.expanduser('~/.dino.cfg'),
]

try:
    env_files.append(os.path.abspath('./dino.cfg'))
except OSError:  # cwd not accessible
    pass

cfg = Config('DINO', env_files=env_files)


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
DEFAULT_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = cfg.get(
    'BASE_DIR', DEFAULT_BASE_DIR, example='/opt/dino',
    doc='Directory to drop internal data; must exist and be writeable and not publicly acccessible.'
)

SECRET_KEY = cfg.get(
    'SECRET_KEY',
    django=True, example='Aixa1ahs1euyo2oopii-Y:eex8sie~d5',
    doc='Long (>64 chars), random and ascii string of characters. Used to derive crypto keys for cookies and other places. Keep secret.'
)
DEBUG = cfg.get(
    'DEBUG', False, bool,
    django=True,
    doc='Run in development mode. Do not enable in production.'
)
ALLOWED_HOSTS = cfg.get(
    'ALLOWED_HOSTS', [], list,
    django=True, example='dino.company.com,dino.internal',
    doc='Comma-seperated list of hostnames under which dino should be accessible at.'
)
PDNS_APIURL = cfg.get(
    'PDNS_APIURL',
    example='https://yourpowerdns.com/api/v1',
    doc='Full URL to your PowerDNS server API endpoint.'
)
PDNS_APIKEY = cfg.get(
    'PDNS_APIKEY',
    example='wooviex7ui0Eiy2Gohth4foovoob5Eip',
    doc='PowerDNS API key from pdns.conf.'
)

# Application definition

INSTALLED_APPS = [
    # disable django development static file handler
    'whitenoise.runserver_nostatic',

    # core apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # 1st party
    'dino.common',
    'dino.zoneeditor',
    'dino.synczones',
    'dino.tenants',

    # 3rd party
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rules.apps.AutodiscoverRulesConfig',
]

for provider in cfg.get('LOGIN_PROVIDERS', [], list):
    INSTALLED_APPS.append(
        f'allauth.socialaccount.providers.{provider}',
    )

try:
    if DEBUG:
        import django_extensions  # noqa
        INSTALLED_APPS += ['django_extensions']
except ImportError:
    print("DEBUG enabled, but django_extensions not installed. skipping app.")

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'csp.middleware.CSPMiddleware',
]

ROOT_URLCONF = 'dino.urls'

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
                'dino.common.context_processors.breadcrumbs',
            ],
        },
    },
]

WSGI_APPLICATION = 'dino.wsgi.application'

# Authentication
# https://docs.djangoproject.com/en/2.1/topics/auth/
# https://django-allauth.readthedocs.io/en/latest/

AUTHENTICATION_BACKENDS = (
    'rules.permissions.ObjectPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

SITE_ID = 1
ACCOUNT_ADAPTER = 'dino.common.allauth.NoNewUsersAccountAdapter'
LOGIN_REDIRECT_URL = '/'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

default_db_url = 'sqlite:///' + os.path.join(BASE_DIR, 'db.sqlite3')
db_url = cfg.get(
    'DB_URL', default_db_url,
    example='mysql://dino:password@host/dino',
    doc='Database to connect to, refer to `dj-database-url <https://github.com/kennethreitz/dj-database-url#url-schema>`_ for information on the URL schema.',
)
DATABASES = {
    'default': dj_database_url.config(default=db_url, conn_max_age=600),
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Proxy Handling

TRUST_PROXY = cfg.get(
    'TRUST_PROXY', False, cast=bool,
    doc='Whether to trust information in X-Forwarded-Proto/Host, or not. Set this, if dino is behind a reverse proxy and it is setting those headers'
)

if TRUST_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True


# HTTPS

HTTPS_ONLY = cfg.get(
    'HTTPS_ONLY', False, cast=bool,
    doc='Whether to enforce HTTPS, set HSTS and send cookies on HTTPS only. Recommended.',
)

if HTTPS_ONLY:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60*60*24*30  # 30 days


# Security Headers

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = cfg.get(
    'TIMEZONE', 'UTC',
    django=True,
    doc='Timezone to use for auditing and logging.'
)

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
# put static files inside module so they can be shipped using setuptools/pip
STATIC_ROOT = os.path.join(DEFAULT_BASE_DIR, 'dino/static.dist')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# Logging
# https://docs.djangoproject.com/en/2.1/topics/logging/
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'rules': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# Custom Settings
ENABLE_SIGNUP = cfg.get(
    'ENABLE_SIGNUP', False, cast=bool,
    doc='Whether to let users create permissionless accounts without any prior authentication.',
)
ZONE_DEFAULT_KIND = cfg.get(
    'ZONE_DEFAULT_KIND', 'Native', cast=bool,
    doc='PowerDNS kind to set for new zones, may be Native, Master or Slave. See `PowerDNS Docs <see https://doc.powerdns.com/authoritative/http-api/zone.html#zone>`_',
)
ZONE_DEFAULT_NAMESERVERS = cfg.get(
    'ZONE_DEFAULT_NAMESERVERS', [], cast=list,
    example='ns1.company.com,ns2.company.com',
    doc='Nameservers to set for new zones.',
)

USE_DEFAULT_RECORD_TYPES = cfg.get(
    'USE_DEFAULT_RECORD_TYPES', True, cast=bool,
    doc='Whether to offer a selection of default record types (A, AAAA, MX, CAA, ...) in the GUI, or rely on DINO_CUSTOM_RECORD_TYPES only.',
)

if USE_DEFAULT_RECORD_TYPES:
    RECORD_TYPES = [
        'A', 'AAAA', 'AFSDB', 'ALIAS', 'CAA', 'CERT', 'CDNSKEY', 'CDS',
        'CNAME', 'DNAME', 'DS', 'KEY', 'LOC', 'MX', 'NAPTR',
        'NS', 'OPENPGPKEY', 'PTR', 'RP', 'SOA', 'SSHFP', 'SRV',
        'TKEY', 'TSIG', 'TLSA', 'SMIMEA', 'TXT', 'URI',
    ]
else:
    RECORD_TYPES = []


CUSTOM_RECORD_TYPES = cfg.get(
    'CUSTOM_RECORD_TYPES', [], cast=list,
    example='X25,SPF,DS',
    doc='Additional record types to offer in the GUI. Any record type can be used here, but PowerDNS or secondary DNS servers might not be able to handle them.',
)
RECORD_TYPES = RECORD_TYPES + CUSTOM_RECORD_TYPES
RECORD_TYPES = [(t, t) for t in RECORD_TYPES]

if not cfg.check_errors():
    sys.exit(1)
