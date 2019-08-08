from WebSDL.settings.base import *

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
if "host" in data:
    ALLOWED_HOSTS.append(data["host"])
if "host_alt" in data:
    ALLOWED_HOSTS.extend(data["host_alt"])
if "host_staging" in data:
    ALLOWED_HOSTS.append(data["host_staging"])

STATIC_ROOT = data["static_root"]
SITE_ROOT = "/opt/websdlenvironment/"
STATIC_URL = '/static/'
SITE_URL = ''
