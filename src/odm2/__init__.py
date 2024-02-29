from odm2.base import ODM2DataModels
from django.conf import settings
import sqlalchemy
from sqlalchemy.orm import sessionmaker, Session

_dbsettings = settings.DATABASES["default"]
_connection_str = f"postgresql://{_dbsettings['USER']}:{_dbsettings['PASSWORD']}@{_dbsettings['HOST']}:{_dbsettings['PORT']}/{_dbsettings['NAME']}"
_engine = sqlalchemy.create_engine(_connection_str, pool_size=10)
_cache_path = settings.DATAMODELCACHE
__session_maker = sessionmaker(_engine)

def create_session() -> Session:
    return __session_maker()

odm2datamodels = ODM2DataModels(_engine, cache_path=_cache_path)
