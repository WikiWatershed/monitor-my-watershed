import json
from tkinter import E
from typing import List, Dict, Any

#PRT - temporarily avoiding the Django models because there appears to be a mismatch for the foreign key
#from dataloaderinterface.models import SensorMeasurement, SiteSensor 
#SiteSensor -> odm2.results
#SensorMeasurement -> odm2.resulttimeseries

from odm2 import Session
from odm2 import engine as _db_engine
from odm2.models.core import SamplingFeatures, Variables, FeatureActions, Units, Results
from odm2.models.results import TimeSeriesResultValues

import sqlalchemy as sqla
from sqlalchemy.sql import func
import pandas as pd
import datetime 

def get_result_timeseries(request_data:Dict[str,Any]) -> str:
	resultid = int(request_data['resultid'])
	interval = int(request_data['interval']) if 'interval' in request_data.keys() else None
	
	with Session() as session:
		filter_args = [TimeSeriesResultValues.resultid == resultid]
		if interval is not None:
			subquery = session.query(func.max(TimeSeriesResultValues.valuedatetime) 
					- datetime.timedelta(days=interval)).\
				filter(TimeSeriesResultValues.resultid == resultid).scalar_subquery()
			filter_args.append(TimeSeriesResultValues.valuedatetime >= subquery)

		query = session.query(TimeSeriesResultValues.valueid, 
					TimeSeriesResultValues.datavalue,
					TimeSeriesResultValues.valuedatetime,
					TimeSeriesResultValues.valuedatetimeutcoffset).\
				filter(*filter_args).\
				order_by(TimeSeriesResultValues.valuedatetime.asc())

		df = pd.read_sql(query.statement, session.bind)
		#df = df.replace(-9999,pd.NA)
		#df = df.dropna()
		df['valuedatetime'] = df['valuedatetime'] + pd.to_timedelta(df['valuedatetimeutcoffset'], unit='hours')
		
		return df.to_json(orient='columns', default_handler=str)

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
			"LEFT JOIN odm2.units AS un ON un.unitsid = rs.unitsid " \
			f"LEFT JOIN odm2.timeseriesresults AS tsr ON tsr.resultid = rs.resultid " \
			f"LEFT JOIN odm2.units AS untrs ON untrs.unitsid = tsr.zlocationunitsid "\
			f"WHERE sf.samplingfeaturecode = '{sampling_feature_code}'; " 
		df = pd.read_sql(query, connection)
		return df.to_json(orient='records', default_handler=str)

def get_sampling_features(request_data:Dict[str,Any]) -> str:
	with Session() as session:
		query = session.query(SamplingFeatures.samplingfeatureuuid, 
			SamplingFeatures.samplingfeaturecode,
			SamplingFeatures.samplingfeaturename).\
			order_by(SamplingFeatures.samplingfeaturecode)
		df = pd.read_sql(query.statement, session.bind)
		return df.to_json(orient='records', default_handler=str)	