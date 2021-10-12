from typing import List, Dict, Any

#PRT - temporarily avoiding the Django models because there appears to be a mismatch for the foreign key
#from dataloaderinterface.models import SensorMeasurement, SiteSensor 
#SiteSensor -> odm2.results
#SensorMeasurement -> odm2.resulttimeseries

import sqlalchemy
import pandas as pd
from django.conf import settings

_dbsettings = settings.DATABASES['odm2']
_connection_str = f"postgresql://{_dbsettings['USER']}:{_dbsettings['PASSWORD']}@{_dbsettings['HOST']}:{_dbsettings['PORT']}/{_dbsettings['NAME']}"
_db_engine = sqlalchemy.create_engine(_connection_str)

def get_result_timeseries(request_data:Dict[str,Any]) -> Dict[str,list]:
	result_id = int(request_data['resultid'])
	
	#PRT - tried the django models approach but these models have odd relationships 
	# and I'm sure this is pulling the correct data. Using sqlalchemy work around for short term
	#timeseries_results = SensorMeasurement.objects.filter(sensor__in=sensors)
	#response = {'data':list(timeseries_results.values())}
	
	#SQL Alchemy work around to models 
	with _db_engine.connect() as connection:
		strsql = f'SELECT valueid, datavalue, valuedatetime, valuedatetimeutcoffset ' \
			f'FROM odm2.timeseriesresultvalues WHERE resultid = {result_id} ' \
			'AND valuedatetime >= ' \
			f'(SELECT MAX(valuedatetime) FROM odm2.timeseriesresultvalues WHERE resultid = {result_id}) ' \
			" - INTERVAL '3 DAYS' "	\
			'ORDER BY valuedatetime;'	
		df = pd.read_sql(strsql, connection)
		return df.to_json(orient='records')
