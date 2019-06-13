from datetime import datetime

import pandas as pd
import numpy as np

from django.conf import settings
from django.db.models import F

from influxdb import DataFrameClient
from influxdb.exceptions import InfluxDBClientError

from dataloader.models import TimeSeriesResultValue


class InfluxHelper(object):
    class MissingConnectionException(Exception):
        """Client is not defined or connected"""
        pass

    def __init__(self, *args, **kwargs):
        self.client = None
        self.batch_size = 10000
        self.connection_info = settings.INFLUX_CONNECTION

    def connect_to_dataframe_client(self):
        self.client = DataFrameClient(
            host=self.connection_info['host'],
            port=self.connection_info['port'],
            username=self.connection_info['username'],
            password=self.connection_info['password'],
            database=self.connection_info['database']
        )

    def recreate_database(self):
        read_user = self.connection_info['read_username']
        database_name = self.connection_info['database']

        if not self.client:
            raise InfluxHelper.MissingConnectionException('InfluxDB client is not connected.')

        self.client.drop_database(database_name)
        self.client.create_database(database_name)
        self.client.grant_privilege('read', database_name, read_user)

    def write_all_sensor_values(self, sensor):
        self.write_sensor_values(sensor, datetime.min)

    def get_series_last_value(self, identifier):
        query_string = 'select last(DataValue), time from {identifier}'.format(identifier=identifier)
        result = self.client.query(query_string, database=self.connection_info['database'])
        if result and len(result) == 1:
            dataframe = result[identifier]  # type: pd.DataFrame
            return dataframe.first_valid_index().to_pydatetime()

    def write_sensor_values(self, sensor, starting_datetime):
        values = TimeSeriesResultValue.objects.filter(value_datetime__gt=starting_datetime, result_id=sensor.result_id)\
            .annotate(DateTime=F('value_datetime'))\
            .annotate(UTCOffset=F('value_datetime_utc_offset'))\
            .annotate(DataValue=F('data_value'))
        values_dataframe = self.prepare_data_values(values)
        if values_dataframe.empty:
            return 0

        result = self.add_dataframe_to_database(values_dataframe, sensor.influx_identifier)
        del values_dataframe
        return result

    def prepare_data_values(self, values_queryset):
        dataframe = pd.DataFrame.from_records(values_queryset.values('DateTime', 'UTCOffset', 'DataValue'))
        if dataframe.empty:
            return dataframe

        dataframe['DateTime'] = pd.to_datetime(dataframe['DateTime'])
        dataframe.set_index(['DateTime'], inplace=True)
        dataframe['DataValue'] = pd.to_numeric(dataframe['DataValue'], errors='coerce').astype(np.float64)
        dataframe['UTCOffset'] = pd.to_numeric(dataframe['UTCOffset'], errors='coerce').astype(np.float64)
        dataframe.dropna(how='any', inplace=True)
        return dataframe

    def add_dataframe_to_database(self, dataframe, identifier):
        try:
            write_success = self.client.write_points(dataframe, identifier, time_precision='s', batch_size=self.batch_size)
            return len(dataframe) if write_success else 0
        except InfluxDBClientError as e:
            print 'Error while writing to database {}: {}'.format(identifier, e.message)
            return 0
