from odm2.base import ODM2DataModels
from django.conf import settings
import sqlalchemy

_dbsettings = settings.DATABASES['default']
_connection_str = f"postgresql://{_dbsettings['USER']}:{_dbsettings['PASSWORD']}@{_dbsettings['HOST']}:{_dbsettings['PORT']}/{_dbsettings['NAME']}"
_engine = sqlalchemy.create_engine(_connection_str, pool_size=10)
_cache_path = settings.DATAMODELCACHE

odm2datamodels = ODM2DataModels(_engine, _cache_path)