import json
import os

from django.conf import settings

from dataloader.models import Organization, Variable, Unit, Result
from dataloaderinterface.models import SiteSensor, SensorMeasurement
from tsa.models import DataSeries


class TimeSeriesAnalystHelper(object):
    wofpy_get_url = 'http://{server}/wofpy/rest/1_1/GetValues' \
                    '?location={sampling_feature_code}&variable={variable_code}&methodCode=2' \
                    '&sourceCode={organization_id}&qualityControlLevelCode=Raw&startDate=&endDate='
    influx_get_url = 'https://{database_server}/query?u=web_client&p=password&db=envirodiy' \
                     '&q=SELECT%20time,%20DataValue::field,%20UTCOffset::field%20FROM%20{influx_identifier}'

    def create_series_from_sensor(self, sensor):
        sensor_queryset = SiteSensor.objects.filter(pk=sensor.pk)
        self.create_series_from_sensors(sensor_queryset)

    def create_series_from_sensors(self, sensors):
        server_data = retrieve_server_data()
        odm2_metadata = self.get_sensors_odm2_metadata(sensors)
        series_objects = [self.generate_data_series(sensor, odm2_metadata, server_data) for sensor in sensors]
        DataSeries.objects.bulk_create(series_objects)

    def update_series_from_sensor(self, sensor):
        # welp, i could've made the update and create in one method
        # if i hadn't started it with the `rebuild_tsa_catalog` command functionality in mind.

        data_series_queryset = DataSeries.objects.filter(result_uuid=sensor.result_uuid)
        if not data_series_queryset.count():
            self.create_series_from_sensor(sensor)
            return

        odm2_metadata = self.get_sensors_odm2_metadata(SiteSensor.objects.filter(pk=sensor.pk))
        last_measurement = SensorMeasurement.objects.filter(sensor=sensor).first()
        data_series_queryset.update(
            variable_code=sensor.sensor_output.variable_code,
            variable_name=sensor.sensor_output.variable_name,
            variable_units_name=sensor.sensor_output.unit_name,
            variable_units_type=odm2_metadata['unit_types'][sensor.sensor_output.unit_id],
            variable_units_abbreviation=sensor.sensor_output.unit_abbreviation,
            sample_medium=sensor.sensor_output.sampled_medium,
            general_category=odm2_metadata['variable_types'][sensor.sensor_output.variable_id],
            utc_offset=get_utc_offset(sensor),
            number_observations=odm2_metadata['values_count'][sensor.result_id],
            date_last_updated=last_measurement and last_measurement.value_datetime,
            is_active=get_is_active(sensor)
        )

    def update_series_from_site(self, registration):
        result_uuids = [uuid[0] for uuid in registration.sensors.values_list('result_uuid')]
        data_series_queryset = DataSeries.objects.filter(result_uuid__in=result_uuids)
        if not data_series_queryset.count():
            self.create_series_from_sensors(registration.sensors.all())
            return

        odm2_metadata = self.get_registration_odm2_metadata(registration)
        data_series_queryset.update(
            site_code=registration.sampling_feature_code,
            site_name=registration.sampling_feature_name,
            latitude=registration.latitude,
            longitude=registration.longitude,
            site_type=registration.site_type,
            source_organization=registration.organization_name or '',
            source_description=odm2_metadata['organization_description'],
        )

    def delete_series_for_sensor(self, sensor):
        DataSeries.objects.filter(result_uuid=sensor.result_uuid).delete()

    def generate_data_series(self, sensor, odm2_metadata, server_data):
        registration = sensor.registration
        last_measurement = SensorMeasurement.objects.filter(sensor=sensor).first()

        return DataSeries(
            result_uuid=str(sensor.result_uuid),
            influx_identifier=get_influx_identifier(sensor),
            source_data_service_id=get_source_id(sensor),
            network=get_network(sensor),
            site_code=registration.sampling_feature_code,
            site_name=registration.sampling_feature_name,
            latitude=registration.latitude,
            longitude=registration.longitude,
            site_type=registration.site_type,
            variable_code=sensor.sensor_output.variable_code,
            variable_name=sensor.sensor_output.variable_name,
            variable_level=get_variable_level(sensor),
            variable_units_name=sensor.sensor_output.unit_name,
            variable_units_type=odm2_metadata['unit_types'][sensor.sensor_output.unit_id],
            variable_units_abbreviation=sensor.sensor_output.unit_abbreviation,
            sample_medium=sensor.sensor_output.sampled_medium,
            value_type=get_value_type(sensor),
            data_type=get_data_type(sensor),
            general_category=odm2_metadata['variable_types'][sensor.sensor_output.variable_id],
            quality_control_level_code=get_processing_level_code(sensor),
            quality_control_level_definition=get_processing_level_definition(sensor),
            quality_control_level_explanation=get_processing_level_explanation(sensor),
            source_organization=registration.organization_name or '',
            source_description=odm2_metadata['organization_descriptions'][registration.organization_id] if registration.organization_id else '',
            begin_datetime=registration.registration_date,
            utc_offset=get_utc_offset(sensor),
            number_observations=odm2_metadata['values_count'][sensor.result_id],
            date_last_updated=last_measurement and last_measurement.value_datetime,
            is_active=get_is_active(sensor),
            get_data_url=self.wofpy_get_url.format(
                server=server_data['server'],
                sampling_feature_code=registration.sampling_feature_code,
                variable_code=sensor.sensor_output.variable_code,
                organization_id=registration.organization_id
            ),
            get_data_influx=self.influx_get_url.format(
                database_server=server_data['database_server'],
                influx_identifier=get_influx_identifier(sensor)
            ),
            no_data_value=get_no_data_value(sensor)
        )

    def get_sensors_odm2_metadata(self, sensors):
        organization_ids = [id[0] for id in sensors.values_list('registration__organization_id')]
        variable_ids = [id[0] for id in sensors.values_list('sensor_output__variable_id')]
        unit_ids = [id[0] for id in sensors.values_list('sensor_output__unit_id')]
        result_ids = [id[0] for id in sensors.values_list('result_id')]
    
        return {
            'organization_descriptions': {
                id: definition
                for (id, definition) in Organization.objects.filter(organization_id__in=organization_ids).values_list('organization_id', 'organization_description')
            },
            'variable_types': {
                id: variable_type
                for (id, variable_type) in Variable.objects.filter(variable_id__in=variable_ids).values_list('variable_id', 'variable_type_id')
            },
            'unit_types': {
                id: unit_type
                for (id, unit_type) in Unit.objects.filter(unit_id__in=unit_ids).values_list('unit_id', 'unit_type_id')
            },
            'values_count': {
                id: value_count
                for (id, value_count) in Result.objects.filter(result_id__in=result_ids).values_list('result_id', 'value_count')
            }
        }

    def get_registration_odm2_metadata(self, registration):
        organization = Organization.objects.filter(organization_id=registration.organization_id).first()
        return {
            'organization_description': organization and organization.organization_description or '',
        }

def retrieve_server_data():
    server_data = {'server': None, 'database_server': None}

    try:
        with open(os.path.join(settings.BASE_DIR, 'settings', 'settings.json')) as data_file:
            data = json.load(data_file)
        server_data['server'] = data['host']
        server_data['database_server'] = next(db_connection['host'] for db_connection in data['databases'] if db_connection['name'] == 'tsa_catalog')
    except IOError:
        print('Error reading settings.json file')

    return server_data


def get_influx_identifier(sensor):
    return 'uuid_{}'.format(str(sensor.result_uuid).replace('-', '_'))


def get_processing_level_explanation(sensor):
    """ Hook for someone to somehow figure out the right QualityControlLevelExplanation"""
    return ''


def get_processing_level_definition(sensor):
    """ Hook for someone to somehow figure out the right QualityControlLevelDefinition"""
    return 'Raw Data'


def get_processing_level_code(sensor):
    """ Hook for someone to somehow figure out the right QualityControlLevelCode"""
    return 'Raw'


def get_data_type(sensor):
    """ Hook for someone to somehow figure out the right DataType"""
    return 'Average'


def get_no_data_value(sensor):
    """ Hook for someone to somehow figure out the right NoDataValue"""
    return -9999


def get_is_active(sensor):
    """ Hook for someone to somehow figure out the right IsActive"""
    return 1


def get_utc_offset(sensor):
    """ Hook for someone to somehow figure out the right UTCOffset"""
    return 0


def get_source_id(sensor):
    """ Hook for someone to somehow figure out the right SourceDataServiceID"""
    return 1


def get_network(sensor):
    """ Hook for someone to somehow figure out the right Network"""
    return 'EnviroDIY'


def get_variable_level(sensor):
    """ Hook for someone to somehow figure out the right VariableLevel"""
    return 'Common'


def get_value_type(sensor):
    """ Hook for someone to somehow figure out the right ValueType"""
    return 'Field Observation'
