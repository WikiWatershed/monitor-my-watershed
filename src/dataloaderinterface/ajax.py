import json
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

def get_result_timeseries_recent(request_data:Dict[str,Any]) -> str:
	result_id = int(request_data['resultid'])
	
	#PRT - tried the django models approach but these models have odd relationships 
	# and I'm sure this is pulling the correct data. Using sqlalchemy work around for short term
	#timeseries_results = SensorMeasurement.objects.filter(sensor__in=sensors)
	#response = {'data':list(timeseries_results.values())}
	
	#SQL Alchemy work around to models 
	with _db_engine.connect() as connection:
		query = f'SELECT valueid, datavalue, valuedatetime, valuedatetimeutcoffset ' \
			f'FROM odm2.timeseriesresultvalues WHERE resultid = {result_id} ' \
			'AND valuedatetime >= ' \
			f'(SELECT MAX(valuedatetime) FROM odm2.timeseriesresultvalues WHERE resultid = {result_id}) ' \
			" - INTERVAL '3 DAYS' "	\
			'ORDER BY valuedatetime;'	
		df = pd.read_sql(query, connection)
		return df.to_json(orient='records')

def get_result_timeseries(request_data:Dict[str,Any]) -> str:
	result_id = int(request_data['resultid'])
	start_date = str(request_data['startdate'])
	end_date = str(request_data['enddate'])

	with _db_engine.connect() as connection:		
		query = f'SELECT valueid, datavalue, valuedatetime, valuedatetimeutcoffset ' \
			f'FROM odm2.timeseriesresultvalues WHERE resultid = {result_id} ' \
			f"AND valuedatetime >= '{start_date}' " \
			f"AND valuedatetime <= '{end_date}' "\
			'ORDER BY valuedatetime;'	
		df = pd.read_sql(query, connection)
		data = df.to_json(orient='columns')
		response = f'{{"result_id":{result_id}, "data":{data} }}'
		return response

def get_sampling_feature_metadata(request_data:Dict[str,Any]) -> str:
	sampling_feature_code = str(request_data['sampling_feature_code'])

	with _db_engine.connect() as connection:
		query = f"SELECT  rs.resultid, rs.resultuuid, samplingfeaturecode, "\
			"samplingfeaturename, sampledmediumcv, un.unitsabbreviation, "\
			"un.unitsname, variablenamecv, variablecode, zlocation, " \
			"untrs.unitsabbreviation AS zlocationunits " \
			"FROM odm2.samplingfeatures AS sf " \
			"JOIN odm2.featureactions AS fa ON fa.samplingfeatureid=sf.samplingfeatureid " \
			"JOIN odm2.results AS rs ON rs.featureactionid = fa.featureactionid " \
			"JOIN odm2.variables AS vr ON vr.variableid = rs.variableid " \
			"JOIN odm2.units AS un ON un.unitsid = rs.unitsid " \
			f"JOIN odm2.timeseriesresults AS tsr ON tsr.resultid = rs.resultid " \
			f"JOIN odm2.units AS untrs ON untrs.unitsid = tsr.zlocationunitsid "\
			f"WHERE sf.samplingfeaturecode = '{sampling_feature_code}'; " 
		df = pd.read_sql(query, connection)
		return df.to_json(orient='records', default_handler=str)


"""
SELECT rs.resultid, rs.resultuuid, samplingfeaturecode, samplingfeaturename, sampledmediumcv, un.unitsabbreviation, 
un.unitsname, variablenamecv, variablecode, zlocation, untrs.unitsabbreviation AS zlocationunits
FROM odm2.samplingfeatures AS sf
JOIN odm2.featureactions AS fa ON fa.samplingfeatureid=sf.samplingfeatureid
JOIN odm2.results AS rs ON rs.featureactionid = fa.featureactionid
JOIN odm2.variables AS vr ON vr.variableid = rs.variableid
JOIN odm2.units AS un ON un.unitsid = rs.unitsid
JOIN odm2.timeseriesresults AS tsr ON tsr.resultid = rs.resultid
JOIN odm2.units AS untrs ON untrs.unitsid = tsr.zlocationunitsid 
WHERE sf.samplingfeaturecode = 'CWS-ThomasDairy2'; 	


"""