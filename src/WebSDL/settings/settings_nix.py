from .linux_server import *
from os import environ

DEBUG = True

# We load the secret key from the environment to not have it in /nix/store.
SECRET_KEY=environ.get('SECRET_KEY')

# The static root will be a path under /nix/store/ which we don't know yet.
STATIC_ROOT=environ.get('STATIC_ROOT')

# Allowed hosts are provided via nix config
ALLOWED_HOSTS = list(environ.get('ALLOWED_HOSTS', default='').split(','))

### Postgres Database Connection
# We use a local (non TCP) DB connection by setting HOST to an empty string
# In this mode the user gets authenticated via the OS.
# Only processes of a specific system user will be able to access the DB
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': environ.get('DB_NAME'),
        'HOST': '',
        'PORT': 0,
        'OPTIONS': {
            # ensure django can work with the ODM2 schema by adding that
            # to the schema search path
            'options': '-c search_path=ODM2,public',
        }
    }
}

# We're using a python module to server static files. Scared of it?
# Read here: http://whitenoise.evans.io/en/stable/index.html#infrequently-asked-questions
MIDDLEWARE += [ 'whitenoise.middleware.WhiteNoiseMiddleware' ]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# default sqlalchemy cache dir is in the store which can never be written to,
# so we put it in an instance specific temporary diretory. but then does
# it actually help? don't quite trust caching anyhow and this should be a
# relatively long-running process
import tempfile

_td = tempfile.TemporaryDirectory()
DATAMODELCACHE = _td.name + "/modelcache.pickle"
