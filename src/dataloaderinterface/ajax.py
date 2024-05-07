from typing import List, Dict, Any

from odm2 import odm2datamodels
odm2_engine = odm2datamodels.odm2_engine
models = odm2datamodels.models

import sqlalchemy
from sqlalchemy.sql import func
import pandas as pd
import datetime 

def get_result_timeseries(request_data:Dict[str,Any]) -> str:
	resultid = int(request_data['resultid'])
	interval = int(request_data['interval']) if 'interval' in request_data.keys() else None
	orient = request_data['orient'] if 'orient' in request_data.keys() else 'columns'
	start_date = request_data['start_date'] if 'start_date' in request_data.keys() else None
	if start_date: start_date = datetime.datetime.fromisoformat(start_date.rstrip('Z')) 
	end_date = request_data['end_date'] if 'end_date' in request_data.keys() else None
	if end_date: end_date = datetime.datetime.fromisoformat(end_date.rstrip('Z')) 

	query = sqlalchemy.select(models.TimeSeriesResultValues.valueid, 
				models.TimeSeriesResultValues.datavalue,
				models.TimeSeriesResultValues.valuedatetime,
				models.TimeSeriesResultValues.valuedatetimeutcoffset).\
			filter(models.TimeSeriesResultValues.resultid == resultid)
	if interval is not None:
		filter_args = [models.TimeSeriesResultValues.resultid == resultid]
		subquery = sqlalchemy.select(func.max(models.TimeSeriesResultValues.valuedatetime) 
				- datetime.timedelta(days=interval)).\
			filter(models.TimeSeriesResultValues.resultid == resultid).scalar_subquery()
		filter_args.append(models.TimeSeriesResultValues.valuedatetime >= subquery)
		query = query.filter(*filter_args).\
			order_by(models.TimeSeriesResultValues.valuedatetime.asc())
	elif start_date is not None and end_date is not None:
		query = query.filter(models.TimeSeriesResultValues.valuedatetime >= start_date) \
			.filter(models.TimeSeriesResultValues.valuedatetime <= end_date) \
			.order_by(models.TimeSeriesResultValues.valuedatetime.asc())

	df = odm2_engine.read_query(query, output_format='dataframe') 
	df['valuedatetime'] = df['valuedatetime'] + pd.to_timedelta(df['valuedatetimeutcoffset'], unit='hours')
	return df.to_json(orient=orient, default_handler=str)

def get_sampling_feature_metadata(request_data:Dict[str,Any]) -> str:
	sampling_feature_code = str(request_data['sampling_feature_code'])

	#TODO - we should convert this to models instead of raw SQL
	with odm2_engine.session_maker() as session:
		query = f"SELECT  rs.resultid, rs.resultuuid, samplingfeaturecode, "\
			"samplingfeaturename, sampledmediumcv, un.unitsabbreviation, "\
			"un.unitsname, variablenamecv, variablecode, zlocation, " \
			"untrs.unitsabbreviation AS zlocationunits " \
			"FROM odm2.samplingfeatures AS sf " \
			"JOIN odm2.featureactions AS fa ON fa.samplingfeatureid=sf.samplingfeatureid " \
			"JOIN odm2.results AS rs ON rs.featureactionid = fa.featureactionid " \
			"JOIN odm2.variables AS vr ON vr.variableid = rs.variableid " \
			"LEFT JOIN odm2.units AS un ON un.unitsid = rs.unitsid " \
			f"LEFT JOIN odm2.timeseriesresults AS tsr ON tsr.resultid = rs.resultid " \
			f"LEFT JOIN odm2.units AS untrs ON untrs.unitsid = tsr.zlocationunitsid "\
			f"WHERE sf.samplingfeaturecode = %(sf_id)s ;" 
		df = pd.read_sql(query, session.bind, params={'sf_id':sampling_feature_code})
		return df.to_json(orient='records', default_handler=str)

def get_sampling_features(request_data:Dict[str,Any]) -> str:
	query = sqlalchemy.select(models.SamplingFeatures.samplingfeatureuuid, 
		models.SamplingFeatures.samplingfeaturecode,
		models.SamplingFeatures.samplingfeaturename).\
		order_by(models.SamplingFeatures.samplingfeaturecode)
	return odm2_engine.read_query(query)