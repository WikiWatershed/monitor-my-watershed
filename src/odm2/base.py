import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declared_attr, declarative_base

import pickle

from django.conf import settings

_dbsettings = settings.DATABASES['default']
_connection_str = f"postgresql://{_dbsettings['USER']}:{_dbsettings['PASSWORD']}@{_dbsettings['HOST']}:{_dbsettings['PORT']}/{_dbsettings['NAME']}"
engine = sqlalchemy.create_engine(_connection_str, pool_size=10)
Session = sqlalchemy.orm.sessionmaker(engine)

cache_path = settings.DATAMODELCACHE

class Base():
    
    @declared_attr
    def __tablename__(self) -> str:
        cls_name = str(self.__name__)
        return cls_name.lower()

_model_base = None
cached = None
try:
    with open(cache_path, 'rb') as file:
        metadata = pickle.load(file=file)
        _model_base = declarative_base(cls=Base, bind=engine, metadata=metadata)
        cached = True
except: 
    metadata = sqlalchemy.MetaData(schema='odm2')
    _model_base = automap_base(cls=Base, metadata=metadata)