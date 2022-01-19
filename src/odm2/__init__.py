from odm2 import base as _base
import pickle as _pickle
import odm2.models as models 

engine = _base.engine
sessionmaker = _base.sessionmaker

if not _base.cached:
	_base._model_base.prepare(engine)
	with open(_base.cache_path, 'wb') as file:
		_pickle.dump(_base._model_base.metadata, file)
