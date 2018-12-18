import codecs
import csv
import os
from collections import OrderedDict
from datetime import timedelta, datetime

from StringIO import StringIO

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from django.http.response import HttpResponse
from django.views.generic.base import View
from django.db.models import QuerySet
from django.shortcuts import reverse
from rest_framework.generics import GenericAPIView
from unicodecsv.py2 import UnicodeWriter

from dataloader.models import SamplingFeature, TimeSeriesResultValue, Unit, EquipmentModel, TimeSeriesResult, Result
from django.db.models.expressions import F
from django.utils.dateparse import parse_datetime
from rest_framework import exceptions
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from dataloaderinterface.forms import SiteSensorForm, SensorDataForm
from dataloaderinterface.models import SiteSensor, SiteRegistration, SensorOutput, SensorMeasurement
from dataloaderservices.auth import UUIDAuthentication
from dataloaderservices.serializers import OrganizationSerializer

from leafpack.models import LeafPack

# TODO: Check user permissions to edit, add, or remove stuff with a permissions class.
# TODO: Use generic api views for create, edit, delete, and list.


class ModelVariablesApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def get(self, request, format=None):
        if 'equipment_model_id' not in request.GET:
            return Response({'error': 'Equipment Model Id not received.'})

        equipment_model_id = request.GET['equipment_model_id']
        if equipment_model_id == '':
            return Response({'error': 'Empty Equipment Model Id received.'})

        equipment_model = EquipmentModel.objects.filter(pk=equipment_model_id).first()
        if not equipment_model:
            return Response({'error': 'Equipment Model not found.'})

        output = equipment_model.instrument_output_variables.values('variable', 'instrument_raw_output_unit')

        return Response(output)


class OutputVariablesApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request):
        output = SensorOutput.objects.for_filters()
        return Response(output)


class RegisterSensorApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def post(self, request, format=None):
        form = SiteSensorForm(data=request.POST)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        registration = form.cleaned_data['registration']
        sensor_output = form.cleaned_data['output_variable']
        height = form.cleaned_data['height']
        notes = form.cleaned_data['sensor_notes']

        site_sensor = SiteSensor.objects.create(registration=registration, sensor_output=sensor_output, height=height, sensor_notes=notes)
        return Response(model_to_dict(site_sensor, fields=[field.name for field in site_sensor._meta.fields]), status=status.HTTP_201_CREATED)


class EditSensorApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def post(self, request, format=None):
        if 'id' not in request.POST:
            return Response({'id': 'No sensor id in the request.'}, status=status.HTTP_400_BAD_REQUEST)

        sensor = SiteSensor.objects.filter(pk=request.POST['id']).first()
        if not sensor:
            return Response({'id': 'Sensor not found.'}, status=status.HTTP_404_NOT_FOUND)

        form = SiteSensorForm(data=request.POST, instance=sensor)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        sensor.sensor_output = form.cleaned_data['output_variable']
        sensor.height = form.cleaned_data['height']
        sensor.sensor_notes = form.cleaned_data['sensor_notes']
        sensor.save(update_fields=['sensor_output', 'height', 'sensor_notes'])
        return Response(model_to_dict(sensor, fields=[field.name for field in sensor._meta.fields]), status=status.HTTP_202_ACCEPTED)


class DeleteSensorApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def post(self, request, format=None):
        if 'id' not in request.POST:
            return Response({'id': 'No sensor id in the request.'}, status=status.HTTP_400_BAD_REQUEST)

        sensor = SiteSensor.objects.filter(pk=request.POST['id']).first()
        if not sensor:
            return Response({'id': 'Sensor not found.'}, status=status.HTTP_404_NOT_FOUND)

        deleted = sensor.delete()
        return Response(deleted, status=status.HTTP_202_ACCEPTED)


class DeleteLeafpackApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def post(self, request, format=None):
        if 'id' not in request.POST:
            return Response({'id': 'No leafpack id in the request.'}, status=status.HTTP_400_BAD_REQUEST)

        leafpack = LeafPack.objects.filter(pk=request.POST['id']).first()
        if not leafpack:
            return Response({'id': 'Leafpack not found.'}, status=status.HTTP_404_NOT_FOUND)

        deleted = leafpack.delete()
        return Response(deleted, status=status.HTTP_202_ACCEPTED)


class OrganizationApi(APIView):
    authentication_classes = (SessionAuthentication, )

    def post(self, request, format=None):
        organization_serializer = OrganizationSerializer(data=request.data)

        if organization_serializer.is_valid():
            organization_serializer.save()
            return Response(organization_serializer.data, status=status.HTTP_201_CREATED)

        error_data = dict(organization_serializer.errors)
        return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)


class FollowSiteApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        action = request.data['action']
        sampling_feature_code = request.data['sampling_feature_code']
        site = SiteRegistration.objects.get(sampling_feature_code=sampling_feature_code)

        if action == 'follow':
            request.user.followed_sites.add(site)
        elif action == 'unfollow':
            request.user.followed_sites.remove(site)

        return Response({}, status.HTTP_200_OK)


class SensorDataUploadView(APIView):
    authentication_classes = (SessionAuthentication,)
    header_row_indicators = ('Data Logger', 'Sampling Feature',
                             'Sensor', 'Variable', 'Result', 'Date and Time')

    def should_skip_row(self, row):
        if row[0].startswith(self.header_row_indicators):
            return True

    def build_results_dict(self, data_file):
        results = {'utc_offset': 0, 'site_uuid': '', 'results': {}}
        got_feature_uuid = False
        got_result_uuids = False
        got_UTC_offset = False

        for index, row in enumerate(csv.reader(data_file)):

            if row[0].startswith('Sampling Feature') and not got_feature_uuid:
                    results['site_uuid'] = row[0].replace(
                        'Sampling Feature UUID: ', '').replace(
                        'Sampling Feature: ', '')
                    got_feature_uuid = True

                    # oldest csv's from modular sensors have the result UUID's
                    # in the same row as the sampling feature UUID
                    # build dict with the rest of the columns
                    if row[1] != '' and not got_result_uuids:
                        results['results'] = {uuid:
                                              {'index': uuid_index,
                                               'values': []
                                               } for uuid_index, uuid in
                                              enumerate(row[1:], start=1)}
                        got_result_uuids = True

            elif row[0].startswith('Result UUID:') and not got_result_uuids:
                results['results'] = {uuid:
                                      {'index': uuid_index,
                                       'values': []
                                       } for uuid_index, uuid in
                                      enumerate(row[1:], start=1)}
                got_result_uuids = True

            elif row[0].startswith('Date and Time'):
                results['utc_offset'] = int(row[0].replace(
                    'Date and Time in UTC', '').replace('+', ''))
                got_UTC_offset = True

            if got_feature_uuid and got_result_uuids and got_UTC_offset:
                break

        return results

    def post(self, request, *args, **kwargs):
        if 'registration_id' not in kwargs:
            return Response({'error': 'No registration specified'}, status=status.HTTP_400_BAD_REQUEST)

        registration = SiteRegistration.objects.prefetch_related('sensors').filter(pk=kwargs['registration_id']).first()
        if not registration:
            return Response({'error:': 'Registration not found'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.can_administer_site(registration):
            return Response({'error': 'Not allowed to edit this site'}, status=status.HTTP_403_FORBIDDEN)

        form = SensorDataForm(request.POST, request.FILES)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        data_file = request.FILES['data_file']
        results_mapping = self.build_results_dict(data_file)

        if str(registration.sampling_feature.sampling_feature_uuid) != results_mapping['site_uuid']:
            return Response({'error': 'This file corresponds to another site.'}, status=status.HTTP_406_NOT_ACCEPTABLE)

        data_value_units = Unit.objects.get(unit_name='hour minute')
        sensors = registration.sensors.all()

        reader = csv.reader(data_file)
        for row in reader:
            if self.should_skip_row(row):
                continue
            else:
                # process data series
                try:
                    measurement_datetime = parse_datetime(row[0])
                except ValueError:
                    print('invalid date {}'.format(row[0]))
                    continue

                if not measurement_datetime:
                    print('invalid date format {}'.format(row[0]))
                    continue

                measurement_datetime = measurement_datetime.replace(tzinfo=None) - timedelta(hours=results_mapping['utc_offset'])

                for sensor in sensors:
                    uuid = str(sensor.result_uuid)
                    if uuid not in results_mapping['results']:
                        print('uuid {} in file does not correspond to a measured variable in {}'.format(uuid, registration.sampling_feature_code))
                        continue

                    data_value = row[results_mapping['results'][uuid]['index']]

                    results_mapping['results'][uuid]['values'].append((
                        long((measurement_datetime - datetime.utcfromtimestamp(0)).total_seconds()),  # -> timestamp
                        data_value  # -> data value (duh)
                    ))

                    try:
                        # Create data value
                        TimeSeriesResultValue.objects.create(
                            result_id=sensor.result_id,
                            value_datetime_utc_offset=results_mapping['utc_offset'],
                            value_datetime=measurement_datetime,
                            censor_code_id='Not censored',
                            quality_code_id='None',
                            time_aggregation_interval=1,
                            time_aggregation_interval_unit=data_value_units,
                            data_value=data_value
                        )
                    except IntegrityError as ie:
                        print('value not created for {}'.format(uuid))
                        continue

        print('updating sensor metadata')
        for sensor in sensors:
            uuid = str(sensor.result_uuid)
            if uuid not in results_mapping['results']:
                print('uuid {} in file does not correspond to a measured variable in {}'.format(uuid, registration.sampling_feature_code))
                continue

            last_data_value = row[results_mapping['results'][uuid]['index']]

            # create last measurement object
            last_measurement = SensorMeasurement.objects.filter(sensor=sensor).first()
            if not last_measurement or last_measurement and last_measurement.value_datetime < measurement_datetime:
                last_measurement and last_measurement.delete()
                SensorMeasurement.objects.create(
                    sensor=sensor,
                    value_datetime=measurement_datetime,
                    value_datetime_utc_offset=timedelta(hours=results_mapping['utc_offset']),
                    data_value=last_data_value
                )

            # Insert data values into influx instance.
            influx_request_url = settings.INFLUX_UPDATE_URL
            influx_series_template = settings.INFLUX_UPDATE_BODY

            all_values = results_mapping['results'][uuid]['values']  # -> [(timestamp, data_value), ]
            influx_request_body = '\n'.join(
                [influx_series_template.format(
                    result_uuid=uuid.replace('-', '_'),
                    data_value=value,
                    utc_offset=results_mapping['utc_offset'],
                    timestamp_s=timestamp
                ) for timestamp, value in all_values]
            )

            requests.post(influx_request_url, influx_request_body.encode())

        # send email informing the data upload is done
        print('sending email')
        subject = 'Data Sharing Portal data upload completed'
        message = 'Your data upload for site {} is complete.'.format(registration.sampling_feature_code)
        sender = "\"Data Sharing Portal Upload\" <data-upload@usu.edu>"
        addresses = [request.user.email]
        if send_mail(subject, message, sender, addresses, fail_silently=True):
            print('email sent!')
        return Response({'message': 'file has been processed successfully'}, status.HTTP_200_OK)


class CSVDataApi(APIView):
    authentication_classes = ()

    date_format = '%Y-%m-%d %H:%M:%S'

    def get(self, request, *args, **kwargs):
        """
        Downloads csv file for given result id's.

        example request to download csv data for one series:
                curl -X GET http://localhost:8000/api/csv-values/?result_id=100

        example request to download csv data for multiple series:
                curl -X GET http://localhost:8000/api/csv-values/?result_id=100&result_id=101&result_id=102
        """
        result_ids = request.GET.getlist('result_id')
        # result_ids = [int(parameter) for parameter in result_parameters if parameter.isdigit()]

        if not len(result_ids):
            return Response({'error': 'Result ID(s) not found.'}, status.HTTP_400_BAD_REQUEST)

        try:
            filename, csv_file = CSVDataApi.generate_csv_file(result_ids, request=request)
        except ValueError as e:
            return Response({'error': e.message}, status.HTTP_404_NOT_FOUND)  # Time Series Result not found.

        response = HttpResponse(csv_file.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
        return response

    @staticmethod
    def generate_csv_file(result_ids, request=None):  # type: (list, any) -> (str, StringIO)
        """
        Gathers time series data for the passed in result id's to generate a csv file for download
        """

        sensors = SiteSensor.objects\
            .prefetch_related('sensor_output', 'registration', 'last_measurement')\
            .filter(result_id__in=result_ids)\
            .order_by('pk')

        if not sensors.count():
            raise ValueError('The results were not found (result id(s): {}).'.format(', '.join(result_ids)))

        csv_file = StringIO()
        csv_writer = UnicodeWriter(csv_file)
        csv_file.write(CSVDataApi.generate_metadata(sensors))
        csv_writer.writerow(CSVDataApi.generate_csv_headers(sensors))
        csv_writer.writerows(CSVDataApi.get_data_values(sensors))

        sensor = sensors.first()

        try:
            resultids_len = len(result_ids)
        except TypeError:
            resultids_len = 1

        if resultids_len > 1:
            filename = "{}_TimeSeriesResults".format(sensor.registration.sampling_feature_code)
        else:
            filename = "{0}_{1}_{2}".format(sensor.registration.sampling_feature_code,
                                            sensor.sensor_output.variable_code, sensor.result_id)

        return filename, csv_file

    @staticmethod
    def generate_csv_headers(sensors):  # type: ([TimeSeriesResult]) -> None
        headers = [u'DateTime', u'TimeOffset', u'DateTimeUTC']
        variable_codes = [sensor.sensor_output.variable_code for sensor in sensors]
        return headers + CSVDataApi.clean_variable_codes(variable_codes)

    @staticmethod
    def clean_variable_codes(varcodes):  # type: ([str]) -> [str]
        """
        Looks for duplicate variable codes and appends a number if collisions exist.

        Example:
            codes = clean_variable_codes(['foo', 'bar', 'foo'])
            print(codes)
            # ['foo-1', 'bar', 'foo-2']
        """
        for varcode in varcodes:
            count = varcodes.count(varcode)
            if count > 1:
                counter = 1
                for i in range(0, len(varcodes)):
                    if varcodes[i] == varcode:
                        varcodes[i] = '{}-{}'.format(varcode, counter)
                        counter += 1
        return varcodes

    @staticmethod
    def get_data_values(sensors):  # type: (QuerySet) -> object
        result_ids = [result_id[0] for result_id in sensors.values_list('result_id')]
        data_values_queryset = TimeSeriesResultValue.objects.filter(result_id__in=result_ids)\
            .order_by('value_datetime')\
            .values('value_datetime', 'value_datetime_utc_offset', 'result_id', 'data_value')

        data_values_map = OrderedDict()
        for value in data_values_queryset:
            data_values_map.setdefault(value['value_datetime'], {}).update({
                'utc_offset': value['value_datetime_utc_offset'],
                value['result_id']: value['data_value']
            })

        data = []
        for timestamp, values in data_values_map.iteritems():
            local_timestamp = timestamp + timedelta(hours=values['utc_offset'])
            row = [
                local_timestamp.strftime(CSVDataApi.date_format),   # Local DateTime
                '{0}:00'.format(values['utc_offset']),              # UTC Offset
                timestamp.strftime(CSVDataApi.date_format)          # UTC DateTime
            ]

            for result_id in result_ids:
                try:
                    row.append(values[result_id])
                except KeyError:
                    row.append('')

            data.append(row)
        return data

    @staticmethod
    def read_file(fname):
        fpath = os.path.join(os.path.dirname(__file__), 'csv_templates', fname)
        with codecs.open(fpath, 'r', encoding='utf-8') as fin:
            return fin.read()

    @staticmethod
    def generate_metadata(sensors):  # type: (QuerySet) -> str
        metadata = str()
        site_sensor = sensors.first()

        # site information
        metadata += CSVDataApi.read_file('site_information.txt').format(site=site_sensor.registration).encode('utf-8')

        # variable information
        variable_template_filename = 'variable_information.txt'
        if sensors.count() > 1:
            variable_template_filename = 'variable_information_compact.txt'
            metadata += "# Variable Information\n# ---------------------------\n"

        variable_template = CSVDataApi.read_file(variable_template_filename)
        for sensor in sensors:
            metadata += variable_template.format(sensor=sensor).encode('utf-8')
        metadata += "#\n"

        # source information
        source_link = reverse('site_detail', kwargs={
            'sampling_feature_code': site_sensor.registration.sampling_feature_code
        })
        metadata += CSVDataApi.read_file('source_information.txt')\
            .format(registration=site_sensor.registration, source_link=source_link)\
            .encode('utf-8')

        # series information
        if sensors.count() == 1:
            metadata += CSVDataApi.read_file('series_information.txt') \
                .format(sensor=site_sensor) \
                .encode('utf-8')

        return metadata


class TimeSeriesValuesApi(APIView):
    authentication_classes = (UUIDAuthentication, )

    def post(self, request, format=None):
        #  make sure that the data is in the request (sampling_feature, timestamp(?), ...) if not return error response
        # if 'sampling_feature' not in request.data or 'timestamp' not in request.data:
        if not all(key in request.data for key in ('timestamp', 'sampling_feature')):
            raise exceptions.ParseError("Required data not found in request.")

        # parse the received timestamp
        try:
            measurement_datetime = parse_datetime(request.data['timestamp'])
        except ValueError:
            raise exceptions.ParseError('The timestamp value is not valid.')

        if not measurement_datetime:
            raise exceptions.ParseError('The timestamp value is not well formatted.')

        if measurement_datetime.utcoffset() is None:
            raise exceptions.ParseError('The timestamp value requires timezone information.')

        utc_offset = int(measurement_datetime.utcoffset().total_seconds() / timedelta(hours=1).total_seconds())

        # saving datetimes in utc time now.
        measurement_datetime = measurement_datetime.replace(tzinfo=None) - timedelta(hours=utc_offset)

        # get odm2 sampling feature if it matches sampling feature uuid sent
        sampling_feature = SamplingFeature.objects.filter(sampling_feature_uuid__exact=request.data['sampling_feature']).first()
        if not sampling_feature:
            raise exceptions.ParseError('Sampling Feature code does not match any existing site.')

        # get all feature actions related to the sampling feature, along with the results, results variables, and actions.
        feature_actions = sampling_feature.feature_actions.prefetch_related('results__variable', 'action').all()
        for feature_action in feature_actions:
            result = feature_action.results.all().first()
            site_sensor = SiteSensor.objects.filter(result_id=result.result_id).first()

            is_first_value = result.value_count == 0

            # don't create a new TimeSeriesValue for results that are not included in the request
            if str(result.result_uuid) not in request.data:
                continue

            result_value = TimeSeriesResultValue(
                result_id=result.result_id,
                value_datetime_utc_offset=utc_offset,
                value_datetime=measurement_datetime,
                censor_code_id='Not censored',
                quality_code_id='None',
                time_aggregation_interval=1,
                time_aggregation_interval_unit=Unit.objects.get(unit_name='hour minute'),
                data_value=request.data[str(result.result_uuid)]
            )

            try:
                result_value.save()
            except Exception as e:
                # continue adding the remaining measurements in the request.
                # TODO: use a logger to log the failed request information.
                continue
                # raise exceptions.ParseError("{variable_code} value not saved {exception_message}".format(
                #     variable_code=result.variable.variable_code, exception_message=e
                # ))

            result.value_count = F('value_count') + 1
            result.result_datetime = measurement_datetime
            result.result_datetime_utc_offset = utc_offset

            # delete last measurement
            last_measurement = SensorMeasurement.objects.filter(sensor=site_sensor).first()
            if not last_measurement:
                SensorMeasurement.objects.create(
                    sensor=site_sensor,
                    value_datetime=result_value.value_datetime,
                    value_datetime_utc_offset=timedelta(hours=result_value.value_datetime_utc_offset),
                    data_value=result_value.data_value
                )
            elif last_measurement and result_value.value_datetime > last_measurement.value_datetime:
                last_measurement and last_measurement.delete()
                SensorMeasurement.objects.create(
                    sensor=site_sensor,
                    value_datetime=result_value.value_datetime,
                    value_datetime_utc_offset=timedelta(hours=result_value.value_datetime_utc_offset),
                    data_value=result_value.data_value
                )

            if is_first_value:
                result.valid_datetime = measurement_datetime
                result.valid_datetime_utc_offset = utc_offset

                if not site_sensor.registration.deployment_date:
                    site_sensor.registration.deployment_date = measurement_datetime
                    site_sensor.registration.deployment_date_utc_offset = utc_offset
                    site_sensor.registration.save(update_fields=['deployment_date'])

            result.save(update_fields=[
                'result_datetime', 'value_count', 'result_datetime_utc_offset',
                'valid_datetime', 'valid_datetime_utc_offset'
            ])

            # Insert data value into influx instance.
            influx_request_url = settings.INFLUX_UPDATE_URL
            influx_request_body = settings.INFLUX_UPDATE_BODY.format(
                result_uuid=str(site_sensor.result_uuid).replace('-', '_'),
                data_value=result_value.data_value,
                utc_offset=result_value.value_datetime_utc_offset,
                timestamp_s=long((result_value.value_datetime - datetime.utcfromtimestamp(0)).total_seconds()),
            )
            requests.post(influx_request_url, influx_request_body.encode())

        return Response({}, status.HTTP_201_CREATED)
