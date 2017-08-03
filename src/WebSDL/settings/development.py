from WebSDL.settings.base import *

DEBUG = True

INTERNAL_IPS = (
    '127.0.0.1',
)

STATIC_ROOT = os.path.join(os.path.join(BASE_DIR, os.pardir), 'dataloaderinterface', 'static')
STATIC_URL = '/static/'
SITE_URL = ''

TEST_RUNNER = 'dataloader.tests.runner.ODM2TestRunner'
