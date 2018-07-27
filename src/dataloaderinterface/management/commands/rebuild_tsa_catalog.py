from django.core.management.base import BaseCommand
from django.db import connection, connections, transaction

from dataloaderinterface.models import SiteSensor


class Command(BaseCommand):
    help = ''

    insert_query = 'INSERT INTO public."DataSeries"({}) VALUES ({});'
    data_series_columns = (
        "SourceDataServiceID", "Network", "SiteCode", "SiteName", "Latitude", "Longitude",
        "SiteType", "VariableCode", "VariableName", "VariableLevel", "VariableUnitsName",
        "VariableUnitsType", "VariableUnitsAbbreviation", "SampleMedium", "ValueType", "DataType", "GeneralCategory",
        "QualityControlLevelCode", "QualityControlLevelDefinition", "QualityControlLevelExplanation",
        "SourceOrganization", "SourceDescription", "BeginDateTime", "UTCOffset", "NumberObservations",
        "DateLastUpdated", "IsActive", "GetDataURL", "GetDataInflux", "ResultUUID", "InfluxIdentifier",
        "NoDataValue"
    )

    wofpy_get_url = 'http://envirodiysandbox.usu.edu/wofpy/rest/1_1/GetValues' \
                    '?location={sampling_feature_code}&variable={variable_code}&methodCode=2' \
                    '&sourceCode={organization_id}&qualityControlLevelCode=Raw&startDate=&endDate='
    influx_get_url = 'http://wpfdbssandbox.uwrl.usu.edu:8086/query?u=web_client&p=password&db=envirodiy' \
                     '&q=SELECT%20time,%20DataValue::field,%20UTCOffset::field%20FROM%20{influx_identifier}'

    def build_query_string(self):
        columns_string = (','.join(['"%s"'] * len(self.data_series_columns))) % self.data_series_columns
        values = ','.join([' %s'] * len(self.data_series_columns))
        return self.insert_query.format(columns_string, values)

    def get_data_series_data(self, sensor):
        print('- getting data series values for sensor {}'.format(sensor.sensor_identity))
        registration = sensor.registration
        result = sensor.result
        return (
            self.get_source_id(sensor),  # -> SourceDataServiceID
            self.get_network(sensor),  # -> Network
            registration.sampling_feature_code,  # -> SiteCode
            registration.sampling_feature_name,  # -> SiteName
            registration.latitude,  # -> Latitude
            registration.longitude,  # -> Longitude
            registration.site_type,  # -> SiteType
            sensor.sensor_output.variable_code,  # -> VariableCode
            sensor.sensor_output.variable_name,  # -> VariableName
            self.get_variable_level(sensor),  # -> VariableLevel
            sensor.sensor_output.unit_name,  # -> VariableUnitsName
            sensor.sensor_output.unit.unit_type_id,  # -> VariableUnitsType
            sensor.sensor_output.unit_abbreviation,  # -> VariableUnitsAbbreviation
            sensor.sensor_output.sampled_medium,  # -> SampleMedium
            self.get_value_type(sensor),  # -> ValueType
            result.timeseriesresult.aggregation_statistic_id,  # -> DataType
            sensor.sensor_output.variable.variable_type_id,  # -> GeneralCategory
            result.processing_level.processing_level_code,  # -> QualityControlLevelCode
            result.processing_level.definition,  # -> QualityControlLevelDefinition
            result.processing_level.explanation or '',  # -> QualityControlLevelExplanation
            registration.organization_name,  # -> SourceOrganization
            registration.organization.organization_description,  # -> SourceDescription
            registration.registration_date,  # -> BeginDateTime
            self.get_utc_offset(sensor),  # -> UTCOffset
            result.value_count,  # -> NumberObservations
            sensor.last_measurement.value_datetime,  # -> DateLastUpdated
            self.get_is_active(sensor),  # -> IsActive
            self.wofpy_get_url.format(  # -> GetDataURL
                sampling_feature_code=registration.sampling_feature_code,
                variable_code=sensor.sensor_output.variable_code,
                organization_id=registration.organization_id
            ),
            self.influx_get_url.format(influx_identifier=self.get_influx_identifier(sensor)),  # -> GetDataInflux
            str(sensor.result_uuid),  # -> ResultUUID
            self.get_influx_identifier(sensor),  # -> InfluxIdentifier
            self.get_no_data_value(sensor)  # -> NoDataValue
        )

    def get_influx_identifier(self, sensor):
        return 'uuid_{}'.format(str(sensor.result_uuid).replace('-', '_'))

    def get_no_data_value(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right NoDataValue"""
        return -9999

    def get_is_active(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right IsActive"""
        return 1

    def get_utc_offset(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right UTCOffset"""
        return 0

    def get_source_id(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right SourceDataServiceID"""
        return 1

    def get_network(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right Network"""
        return 'EnviroDIY'

    def get_variable_level(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right VariableLevel"""
        return 'Common'

    def get_value_type(self, sensor):
        """I have to finish this as fast as i can, so here's a hook to somehow figure out the right ValueType"""
        return 'Field Observation'

    def handle(self, *args, **options):
        sensors = SiteSensor.objects.filter(last_measurement__isnull=False, sensor_output__isnull=False)[:2]
        data_series = tuple(self.get_data_series_data(sensor) for sensor in sensors)
        print('* {} data series collected'.format(len(data_series)))

        with connections['tsa_catalog'].cursor() as cursor:
            print("- DELETING EVERYTHING!")
            cursor.execute('TRUNCATE TABLE public."DataSeries" RESTART IDENTITY')
            cursor.execute('ALTER SEQUENCE public.series_increment RESTART WITH 1;')

            print("- CREATING EVERYTHING BACK AGAIN!")
            cursor.executemany(self.build_query_string(), data_series)

            transaction.commit(using='tsa_catalog')
            print("- DONE!")