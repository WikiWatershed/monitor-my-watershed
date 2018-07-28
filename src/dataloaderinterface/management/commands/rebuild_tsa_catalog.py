import json
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, connections, transaction

from dataloader.models import Organization, Variable, Unit, Result
from dataloaderinterface.models import SiteSensor


class Command(BaseCommand):
    help = ''
    server = ''
    database_server = ''
    organization_descriptions = {}
    variable_types = {}
    unit_types = {}
    values_count = {}

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

    wofpy_get_url = '{server}/wofpy/rest/1_1/GetValues' \
                    '?location={sampling_feature_code}&variable={variable_code}&methodCode=2' \
                    '&sourceCode={organization_id}&qualityControlLevelCode=Raw&startDate=&endDate='
    influx_get_url = '{database_server}:8086/query?u=web_client&p=password&db=envirodiy' \
                     '&q=SELECT%20time,%20DataValue::field,%20UTCOffset::field%20FROM%20{influx_identifier}'

    def retrieve_server_data(self):
        try:
            with open(os.path.join(settings.BASE_DIR, 'settings', 'settings.json')) as data_file:
                data = json.load(data_file)

            self.server = data['host']
            self.database_server = next(db_connection for db_connection in data['databases'] if db_connection.name == 'tsa_catalog')
        except IOError:
            print("Error reading server configuration data (settings.json)")


    def build_query_string(self):
        columns_string = (','.join(['"%s"'] * len(self.data_series_columns))) % self.data_series_columns
        values = ','.join([' %s'] * len(self.data_series_columns))
        return self.insert_query.format(columns_string, values)

    def get_data_series_data(self, sensor):
        print('- getting data series values for sensor {}'.format(sensor.sensor_identity))

        registration = sensor.registration
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
            self.unit_types[sensor.sensor_output.unit_id],  # -> VariableUnitsType
            sensor.sensor_output.unit_abbreviation,  # -> VariableUnitsAbbreviation
            sensor.sensor_output.sampled_medium,  # -> SampleMedium
            self.get_value_type(sensor),  # -> ValueType
            self.get_data_type(sensor),  # -> DataType
            self.variable_types[sensor.sensor_output.variable_id],  # -> GeneralCategory
            self.get_processing_level_code(sensor),  # -> QualityControlLevelCode
            self.get_processing_level_definition(sensor),  # -> QualityControlLevelDefinition
            self.get_processing_level_explanation(sensor),  # -> QualityControlLevelExplanation
            registration.organization_name or '',  # -> SourceOrganization
            self.organization_descriptions[registration.organization_id] if registration.organization_id else '',  # -> SourceDescription
            registration.registration_date,  # -> BeginDateTime
            self.get_utc_offset(sensor),  # -> UTCOffset
            self.values_count[sensor.result_id],  # -> NumberObservations
            sensor.last_measurement.value_datetime,  # -> DateLastUpdated
            self.get_is_active(sensor),  # -> IsActive
            self.wofpy_get_url.format(  # -> GetDataURL
                server=self.server,
                sampling_feature_code=registration.sampling_feature_code,
                variable_code=sensor.sensor_output.variable_code,
                organization_id=registration.organization_id
            ),
            self.influx_get_url.format(
                database_server=self.database_server,
                influx_identifier=self.get_influx_identifier(sensor)
            ),  # -> GetDataInflux
            str(sensor.result_uuid),  # -> ResultUUID
            self.get_influx_identifier(sensor),  # -> InfluxIdentifier
            self.get_no_data_value(sensor)  # -> NoDataValue
        )



    def get_influx_identifier(self, sensor):
        return 'uuid_{}'.format(str(sensor.result_uuid).replace('-', '_'))

    def get_processing_level_explanation(self, sensor):
        """ Hook for someone to somehow figure out the right QualityControlLevelExplanation"""
        return ''

    def get_processing_level_definition(self, sensor):
        """ Hook for someone to somehow figure out the right QualityControlLevelDefinition"""
        return 'Raw Data'

    def get_processing_level_code(self, sensor):
        """ Hook for someone to somehow figure out the right QualityControlLevelCode"""
        return 'Raw'

    def get_data_type(self, sensor):
        """ Hook for someone to somehow figure out the right DataType"""
        return 'Average'

    def get_no_data_value(self, sensor):
        """ Hook for someone to somehow figure out the right NoDataValue"""
        return -9999

    def get_is_active(self, sensor):
        """ Hook for someone to somehow figure out the right IsActive"""
        return 1

    def get_utc_offset(self, sensor):
        """ Hook for someone to somehow figure out the right UTCOffset"""
        return 0

    def get_source_id(self, sensor):
        """ Hook for someone to somehow figure out the right SourceDataServiceID"""
        return 1

    def get_network(self, sensor):
        """ Hook for someone to somehow figure out the right Network"""
        return 'EnviroDIY'

    def get_variable_level(self, sensor):
        """ Hook for someone to somehow figure out the right VariableLevel"""
        return 'Common'

    def get_value_type(self, sensor):
        """ Hook for someone to somehow figure out the right ValueType"""
        return 'Field Observation'

    def load_odm2_related_data(self, sensors):
        organization_ids = [id[0] for id in sensors.values_list('registration__organization_id')]
        self.organization_descriptions = {
            id: definition
            for (id, definition)
            in Organization.objects.filter(organization_id__in=organization_ids).values_list('organization_id', 'organization_description')
        }

        variable_ids = [id[0] for id in sensors.values_list('sensor_output__variable_id')]
        self.variable_types = {
            id: variable_type
            for (id, variable_type)
            in Variable.objects.filter(variable_id__in=variable_ids).values_list('variable_id', 'variable_type_id')
        }

        unit_ids = [id[0] for id in sensors.values_list('sensor_output__unit_id')]
        self.unit_types = {
            id: unit_type
            for (id, unit_type)
            in Unit.objects.filter(unit_id__in=unit_ids).values_list('unit_id', 'unit_type_id')
        }

        result_ids = [id[0] for id in sensors.values_list('result_id')]
        self.values_count = {
            id: value_count
            for (id, value_count)
            in Result.objects.filter(result_id__in=result_ids).values_list('result_id', 'value_count')
        }

    def handle(self, *args, **options):
        sensors = SiteSensor.objects.select_related('registration').prefetch_related('last_measurement', 'sensor_output')\
            .filter(last_measurement__isnull=False, sensor_output__isnull=False)\
            .defer('height', 'sensor_notes', 'registration__site_notes')

        self.retrieve_server_data()
        self.load_odm2_related_data(sensors)
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