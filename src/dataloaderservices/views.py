from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import timedelta, datetime
from io import StringIO
import os
from typing import Union, Dict, Any, Iterable, List, Tuple

from django.conf import settings
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpRequest
from django.views.generic.base import View
from django.db.models import QuerySet
from django.shortcuts import reverse
from django.utils.dateparse import parse_datetime
from django.core.handlers.wsgi import WSGIRequest
from django.conf import settings

from rest_framework import exceptions
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

import pandas as pd
import sqlalchemy
from sqlalchemy.sql import text
import psycopg2

from dataloader.models import SamplingFeature, Unit, EquipmentModel, TimeSeriesResult
from dataloaderinterface.forms import SiteSensorForm, SensorDataForm
from dataloaderinterface.models import (
    SiteSensor,
    SiteRegistration,
    SensorOutput,
    SensorMeasurement,
)
from dataloaderservices.auth import UUIDAuthentication
from dataloaderservices.serializers import OrganizationSerializer
from leafpack.models import LeafPack
from odm2 import odm2datamodels

_dbsettings = settings.DATABASES["default"]
_connection_str = f"postgresql://{_dbsettings['USER']}:{_dbsettings['PASSWORD']}@{_dbsettings['HOST']}:{_dbsettings['PORT']}/{_dbsettings['NAME']}"
_db_engine = sqlalchemy.create_engine(_connection_str, pool_size=10, pool_recycle=1800)

odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models

# TODO: Check user permissions to edit, add, or remove stuff with a permissions class.
# TODO: Use generic api views for create, edit, delete, and list.

class ModelVariablesApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request, format=None):
        if "equipment_model_id" not in request.GET:
            return Response({"error": "Equipment Model Id not received."})

        equipment_model_id = request.GET["equipment_model_id"]
        if equipment_model_id == "":
            return Response({"error": "Empty Equipment Model Id received."})

        equipment_model = EquipmentModel.objects.filter(pk=equipment_model_id).first()
        if not equipment_model:
            return Response({"error": "Equipment Model not found."})

        output = equipment_model.instrument_output_variables.values(
            "variable", "instrument_raw_output_unit"
        )

        return Response(output)


class OutputVariablesApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def get(self, request):
        output = SensorOutput.objects.for_filters()
        return Response(output)


class RegisterSensorApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        form = SiteSensorForm(data=request.POST)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        registration = form.cleaned_data["registration"]
        sensor_output = form.cleaned_data["output_variable"]
        height = form.cleaned_data["height"]
        notes = form.cleaned_data["sensor_notes"]

        # create action-by record
        affiliation = None
        for a in self.request.user.affiliation:
            if a.organization_id == registration.organization_id:
                affiliation = a
                break

        action = registration.sampling_feature.actions.first()
        action.action_by.create(affiliation=affiliation, is_action_lead=True)

        site_sensor = SiteSensor.objects.create(
            registration=registration,
            sensor_output=sensor_output,
            height=height,
            sensor_notes=notes,
        )
        return Response(
            model_to_dict(
                site_sensor, fields=[field.name for field in site_sensor._meta.fields]
            ),
            status=status.HTTP_201_CREATED,
        )


class EditSensorApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        if "id" not in request.POST:
            return Response(
                {"id": "No sensor id in the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sensor = SiteSensor.objects.filter(pk=request.POST["id"]).first()
        if not sensor:
            return Response(
                {"id": "Sensor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        form = SiteSensorForm(data=request.POST, instance=sensor)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        sensor.sensor_output = form.cleaned_data["output_variable"]
        sensor.height = form.cleaned_data["height"]
        sensor.sensor_notes = form.cleaned_data["sensor_notes"]
        sensor.save(update_fields=["sensor_output", "height", "sensor_notes"])
        return Response(
            model_to_dict(sensor, fields=[field.name for field in sensor._meta.fields]),
            status=status.HTTP_202_ACCEPTED,
        )


class DeleteSensorApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        if "id" not in request.POST:
            return Response(
                {"id": "No sensor id in the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sensor = SiteSensor.objects.filter(pk=request.POST["id"]).first()
        if not sensor:
            return Response(
                {"id": "Sensor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        deleted = sensor.delete()
        return Response(deleted, status=status.HTTP_202_ACCEPTED)


class DeleteLeafpackApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        if "id" not in request.POST:
            return Response(
                {"id": "No leafpack id in the request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leafpack = LeafPack.objects.filter(pk=request.POST["id"]).first()
        if not leafpack:
            return Response(
                {"id": "Leafpack not found."}, status=status.HTTP_404_NOT_FOUND
            )

        deleted = leafpack.delete()
        return Response(deleted, status=status.HTTP_202_ACCEPTED)


class OrganizationApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        organization_serializer = OrganizationSerializer(data=request.data)

        if organization_serializer.is_valid():
            organization_serializer.save()
            return Response(
                organization_serializer.data, status=status.HTTP_201_CREATED
            )

        error_data = dict(organization_serializer.errors)
        return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)


class FollowSiteApi(APIView):
    authentication_classes = (SessionAuthentication,)

    def post(self, request, format=None):
        action = request.data["action"]
        sampling_feature_code = request.data["sampling_feature_code"]
        site = SiteRegistration.objects.get(sampling_feature_code=sampling_feature_code)

        if action == "follow":
            request.user.followed_sites.add(site)
        elif action == "unfollow":
            request.user.followed_sites.remove(site)

        return Response({}, status.HTTP_200_OK)


class SensorDataUploadView(APIView):
    authentication_classes = (SessionAuthentication,)
    header_row_indicators = (
        "Data Logger",
        "Sampling Feature",
        "Sensor",
        "Variable",
        "Result",
        "Date and Time",
        "Code",
    )

    def should_skip_row(self, row):
        if row[0].startswith(self.header_row_indicators):
            return True

    def decode_utf8_sig(self, input_iterator: Iterable) -> str:
        for item in input_iterator:
            yield item.decode("utf-8-sig")

    def build_results_dict(self, data_file):
        results = {"utc_offset": 0, "site_uuid": "", "results": {}}
        got_feature_uuid = False
        got_result_uuids = False
        got_UTC_offset = False

        for row in csv.reader(self.decode_utf8_sig(data_file)):
            if row[0].startswith("Sampling Feature") and not got_feature_uuid:
                results["site_uuid"] = (
                    row[0]
                    .replace("Sampling Feature UUID: ", "")
                    .replace("Sampling Feature: ", "")
                )
                got_feature_uuid = True

                # oldest csv's from modular sensors have the result UUID's
                # in the same row as the sampling feature UUID
                # build dict with the rest of the columns
                if len(row) > 1:
                    if row[1] != "" and not got_result_uuids:
                        results["results"] = {
                            uuid: {"index": uuid_index, "values": []}
                            for uuid_index, uuid in enumerate(row[1:], start=1)
                        }
                        got_result_uuids = True

            elif row[0].startswith("Result UUID:") and not got_result_uuids:
                results["results"] = {
                    uuid: {"index": uuid_index, "values": []}
                    for uuid_index, uuid in enumerate(row[1:], start=1)
                }
                got_result_uuids = True

            elif row[0].startswith("Date and Time"):
                results["utc_offset"] = int(
                    row[0].replace("Date and Time in UTC", "").replace("+", "")
                )
                got_UTC_offset = True

            if got_feature_uuid and got_result_uuids and got_UTC_offset:
                break

        return results

    def post(self, request, *args, **kwargs):
        if "registration_id" not in kwargs:
            return Response(
                {"error": "No registration specified"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        registration = (
            SiteRegistration.objects.prefetch_related("sensors")
            .filter(pk=kwargs["registration_id"])
            .first()
        )
        if not registration:
            return Response(
                {"error:": "Registration not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not request.user.can_administer_site(registration.sampling_feature_id):
            return Response(
                {"error": "Not allowed to edit this site"},
                status=status.HTTP_403_FORBIDDEN,
            )

        form = SensorDataForm(request.POST, request.FILES)

        if not form.is_valid():
            error_data = dict(form.errors)
            return Response(error_data, status=status.HTTP_206_PARTIAL_CONTENT)

        data_file = request.FILES["data_file"]
        results_mapping = self.build_results_dict(data_file)

        if (
            str(registration.sampling_feature.sampling_feature_uuid)
            != results_mapping["site_uuid"]
        ):
            return Response(
                {"error": "This file corresponds to another site."},
                status=status.HTTP_406_NOT_ACCEPTABLE,
            )

        data_value_units = Unit.objects.get(unit_name="hour minute")
        sensors = registration.sensors.all()

        result_values = []
        warnings = []
        for row in csv.reader(self.decode_utf8_sig(data_file)):
            if self.should_skip_row(row):
                continue
            else:
                try:
                    measurement_datetime = parse_datetime(row[0])
                    if not measurement_datetime:
                        measurement_datetime = pd.to_datetime(row[0])
                    if not measurement_datetime:
                        raise ValueError
                except (ValueError, TypeError):
                    warnings.append("Unrecognized date format: {}".format(row[0]))
                    continue
                measurement_datetime = measurement_datetime.replace(
                    tzinfo=None
                ) - timedelta(hours=results_mapping["utc_offset"])

                for sensor in sensors:
                    uuid = str(sensor.result_uuid)
                    if uuid not in results_mapping["results"]:
                        # TODO - consider revised approach where we loop over column in CSV and not all sensors
                        # this would allow us to return warning that result uuid is not recognized.
                        continue

                    data_value = row[results_mapping["results"][uuid]["index"]]
                    result_value = TimeseriesResultValueTechDebt(
                            result_id=sensor.result_id,
                            data_value=data_value,
                            utc_offset=results_mapping['utc_offset'],
                            value_datetime=measurement_datetime,
                            censor_code='Not censored',
                            quality_code='None',
                            time_aggregation_interval=1,
                            time_aggregation_interval_unit=data_value_units.unit_id,
                            ) 
                    result_values.append(result_value)

        with _db_engine.begin() as connection:
            insert_timeseries_result_values(result_values, connection)

        # block is responsible for keeping separate dataloader database metadata in sync
        # long term plan is to eliminate this, but need to keep for the now
        for sensor in sensors:
            uuid = str(sensor.result_uuid)
            if uuid not in results_mapping["results"]:
                print(
                    "uuid {} in file does not correspond to a measured variable in {}".format(
                        uuid, registration.sampling_feature_code
                    )
                )
                continue
            last_data_value = row[results_mapping["results"][uuid]["index"]]
            last_measurement = SensorMeasurement.objects.filter(sensor=sensor).first()
            if not last_measurement:
                SensorMeasurement.objects.create(
                    sensor=sensor,
                    value_datetime=measurement_datetime,
                    value_datetime_utc_offset=timedelta(
                        hours=results_mapping["utc_offset"]
                    ),
                    data_value=last_data_value,
                )
        # end meta data syncing block

        # TODO: Decouple email from this method by having email sender class
        # subject = 'Data Sharing Portal data upload completed'
        # message = 'Your data upload for site {} is complete.'.format(registration.sampling_feature_code)
        # sender = "\"Data Sharing Portal Upload\" <data-upload@usu.edu>"
        # addresses = [request.user.email]
        # if send_mail(subject, message, sender, addresses, fail_silently=True):
        #    print('email sent!')
        if warnings:
            return Response({"warnings": warnings}, status.HTTP_206_PARTIAL_CONTENT)
        return Response(
            {"message": "file has been processed successfully"}, status.HTTP_200_OK
        )


class CSVDataApi(View):
    authentication_classes = ()

    date_format = "%Y-%m-%d %H:%M:%S"

    def get(self, request: WSGIRequest, *args, **kwargs) -> HttpResponse:
        """
        Downloads csv file for given result id's.

        example request to download csv data for one series:
                curl -X GET http://localhost:8000/api.csv-values/?result_ids=100

        example request to download csv data for multiple series:
                curl -X GET http://localhost:8000/api.csv-values/?result_ids=100,101,102
        """
        result_ids = []
        if "result_id" in request.GET:
            result_ids = [request.GET.get("result_id", [])]
        elif "result_ids" in request.GET:
            result_ids = request.GET["result_ids"].split(",")

        if not len(result_ids):
            return Response({"error": "Result ID(s) not found."})

        try:
            filename, csv_file = CSVDataApi.get_csv_file(result_ids, request=request)
        except ValueError as e:
            return Response({"error": e.message})  # Time Series Result not found.

        response = HttpResponse(csv_file.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="%s.csv"' % filename
        return response

    @staticmethod
    def get_csv_file(
        result_ids: List[str], request: WSGIRequest = None
    ) -> Tuple[str, StringIO]:
        """
        Gathers time series data for the passed in result id's to generate a csv file for download
        """

        try:
            # Some duck typing here to check if `result_ids` is an iterable,
            # and if it's not, filter using 'pk__in'
            iter(result_ids)
            time_series_result = (
                TimeSeriesResult.objects.prefetch_related(
                    "result__feature_action__action__people"
                )
                .select_related(
                    "result__feature_action__sampling_feature", "result__variable"
                )
                .filter(pk__in=result_ids)
                .order_by("pk")
            )
        except TypeError:
            # If exception is raised, `result_ids` is not an iterable,
            # so filter using 'pk'
            time_series_result = (
                TimeSeriesResult.objects.prefetch_related(
                    "result__feature_action__action__people"
                )
                .select_related(
                    "result__feature_action__sampling_feature", "result__variable"
                )
                .filter(pk=result_ids)
            )

        if not time_series_result.count():
            raise ValueError(
                "Time Series Result(s) not found (result id(s): {}).".format(
                    ", ".join(result_ids)
                )
            )

        csv_file = StringIO()
        csv_writer = csv.writer(csv_file)
        csv_file.write(
            CSVDataApi.generate_metadata(time_series_result, request=request)
        )
        csv_writer.writerow(CSVDataApi.get_csv_headers(time_series_result))
        csv_writer.writerows(CSVDataApi.get_data_values(time_series_result))

        result = time_series_result.first().result

        try:
            resultids_len = len(result_ids)
        except TypeError:
            resultids_len = 1

        if resultids_len > 1:
            filename = "{}_TimeSeriesResults".format(
                result.feature_action.sampling_feature.sampling_feature_code
            )
        else:
            filename = "{0}_{1}_{2}".format(
                result.feature_action.sampling_feature.sampling_feature_code,
                result.variable.variable_code,
                result.result_id,
            )

        return filename, csv_file

    @staticmethod
    def get_csv_headers(ts_results: List[TimeSeriesResult]) -> None:
        headers = ["DateTime", "TimeOffset", "DateTimeUTC"]
        var_codes = [
            ts_result.result.variable.variable_code for ts_result in ts_results
        ]
        return headers + CSVDataApi.clean_variable_codes(var_codes)

    @staticmethod
    def clean_variable_codes(varcodes: List[str]) -> List[str]:
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
                        varcodes[i] = "{}-{}".format(varcode, counter)
                        counter += 1
        return varcodes

    @staticmethod
    def get_data_values(time_series_results: QuerySet) -> object:
        result_ids = [
            result_id[0] for result_id in time_series_results.values_list("pk")
        ]

        query = (
            sqlalchemy.select(
                odm2_models.TimeSeriesResultValues.resultid,
                odm2_models.TimeSeriesResultValues.datavalue,
                odm2_models.TimeSeriesResultValues.valuedatetime,
                odm2_models.TimeSeriesResultValues.valuedatetimeutcoffset,
            )
            .filter(odm2_models.TimeSeriesResultValues.resultid.in_(result_ids))
            .order_by(
                odm2_models.TimeSeriesResultValues.valuedatetime,
                odm2_models.TimeSeriesResultValues.resultid,
            )
        )
        df = odm2_engine.read_query(query, output_format="dataframe")

        # convert into datetime for vector calculation to utc datetime
        df["valuedatetime"] = pd.to_datetime(df["valuedatetime"])
        df["valuedatetime_utc"] = df["valuedatetime"] + pd.to_timedelta(
            df["valuedatetimeutcoffset"], unit="hours"
        )

        piv = pd.pivot_table(
            df,
            ["datavalue"],
            ["valuedatetime", "valuedatetimeutcoffset", "valuedatetime_utc"],
            ["resultid"],
        )

        vals = piv.to_numpy()
        dt = piv.index.get_level_values(0).astype(str)
        utc_off = piv.index.get_level_values(1).astype(str)
        dt_utc = piv.index.get_level_values(2).astype(str)
        z = list(zip(dt, utc_off, dt_utc, vals))
        lst = [[i[0], i[1], i[2], *i[3]] for i in z]

        return lst

    @staticmethod
    def read_file(fname: str) -> str:
        fpath = os.path.join(os.path.dirname(__file__), "csv_templates", fname)
        with open(fpath, "r", encoding="utf8") as f:
            contents = f.read()
        return contents

    @staticmethod
    def generate_metadata(
        time_series_results: QuerySet, request: WSGIRequest = None
    ) -> str:
        metadata = ""

        # Get the first TimeSeriesResult object and use it to get values for the
        # "Site Information" block in the header of the CSV
        tsr = time_series_results.first()
        site_sensor = (
            SiteSensor.objects.select_related("registration")
            .filter(result_id=tsr.result.result_id)
            .first()
        )
        site_info_template = CSVDataApi.read_file("site_information.txt")
        site_info_template = site_info_template.format(site=site_sensor.registration)
        metadata += site_info_template

        time_series_results_as_list = [tsr for tsr in time_series_results]

        if len(time_series_results_as_list) == 1:
            # If there is only one time series result, use the normal variable and method info template
            variablemethodinfo_template = CSVDataApi.read_file(
                "variable_and_method_template.txt"
            )
            tsr = next(iter(time_series_results_as_list))
            metadata += variablemethodinfo_template.format(
                variable_code=tsr.result.variable,
                r=tsr.result,
                v=tsr.result.variable,
                u=tsr.result.unit,
                s=site_sensor,
            )
        else:
            # If there are more than one time series result, use the compact
            # version of the variable and method info template.

            # Write Variable and Method Information data
            metadata += (
                "# Variable and Method Information\n#---------------------------\n"
            )
            variablemethodinfo_template = CSVDataApi.read_file(
                "variable_and_method_template_compact.txt"
            )
            varcodes = [tsr.result.variable for tsr in time_series_results]
            varcodes = CSVDataApi.clean_variable_codes(varcodes)
            for i in range(0, len(time_series_results_as_list)):
                # Yeah, so this is enumerating like this because of the need to append "-#"
                # to variable codes when there are duplicate variable codes. This is so the
                # column names can be distinguished easily.
                tsr = time_series_results_as_list[i]

                sensor = (
                    SiteSensor.objects.select_related("registration")
                    .filter(result_id=tsr.result.result_id)
                    .first()
                )

                # Why use `varcodes[i]` instead of simply `tsr.result.variable`? Because
                # there is a possibility of having duplicate variable codes, and
                # `varcodes` is passed into `CSVDataApi.clean_variable_codes(*arg)`
                # which does additional formatting to the variable code names.
                metadata += variablemethodinfo_template.format(
                    variable_code=varcodes[i],
                    r=tsr.result,
                    v=tsr.result.variable,
                    u=tsr.result.unit,
                    s=sensor,
                )

        metadata += "#\n"

        if len(time_series_results) == 1:
            # If there's only one timeseriesresult, add the variable and unit information block.
            # When there are multiple timeseriesresults, this part of the CSV becomes cluttered
            # and unreadable.
            tsr = time_series_results.first()
            metadata += CSVDataApi.read_file(
                "variable_and_unit_information.txt"
            ).format(
                variable=tsr.result.variable, unit=tsr.result.unit, sensor=site_sensor
            )

        # Write Source Information data

        # affiliation = tsr.result.feature_action.action.people.first()
        # affiliation = site_sensor.registration.odm2_affiliation
        organization = site_sensor.registration.organization
        annotation = tsr.result.annotations.first()
        citation = (
            annotation.citation.title if annotation and annotation.citation else ""
        )

        if request:
            source_link = request.build_absolute_uri(
                reverse(
                    "site_detail",
                    kwargs={
                        "sampling_feature_code": site_sensor.registration.sampling_feature_code
                    },
                )
            )
        else:
            source_link = reverse(
                "site_detail",
                kwargs={
                    "sampling_feature_code": site_sensor.registration.sampling_feature_code
                },
            )

        metadata += CSVDataApi.read_file("source_info_template.txt").format(
            organization=organization, citation=citation, source_link=source_link
        )

        return metadata


class TimeSeriesValuesApi(APIView):
    authentication_classes = (UUIDAuthentication,)

    def post(self, request, format=None):
        if not all(key in request.data for key in ("timestamp", "sampling_feature")):
            raise exceptions.ParseError("Required data not found in request.")
        
        sampling_feature = SamplingFeature.objects.filter(sampling_feature_uuid__exact=request.data.pop("sampling_feature")).first()
        if not sampling_feature:
            raise exceptions.ParseError('Sampling Feature code does not match any existing site.')
        
        unit_id = Unit.objects.get(unit_name='hour minute').unit_id

        measurement_datetimes = []
        timestamps = request.data.pop("timestamp")
        if not isinstance(timestamps, list):
            timestamps = [timestamps]
        for timestamp in timestamps:
            try:
                measurement_datetime = parse_datetime(timestamp)
            except ValueError:
                raise exceptions.ParseError('The timestamp value is not valid.')
            if not measurement_datetime:
                raise exceptions.ParseError('The timestamp value is not well formatted.')
            if measurement_datetime.utcoffset() is None:
                raise exceptions.ParseError('The timestamp value requires timezone information.')
            utc_offset = int(measurement_datetime.utcoffset().total_seconds() / timedelta(hours=1).total_seconds())
            measurement_datetime = measurement_datetime.replace(tzinfo=None) - timedelta(hours=utc_offset)
            measurement_datetimes.append((measurement_datetime, utc_offset))

        num_measurements = len(measurement_datetimes)
        measurement_data = {k: v if isinstance(v, list) else [v]
            for k, v in request.data.items()}

        if not all(len(m) == num_measurements for m in measurement_data.values()):
            raise exceptions.ParseError("unequal number of data points")

        with _db_engine.begin() as connection:
            result_uuids = get_result_UUIDs(sampling_feature.sampling_feature_id, connection)
            if not result_uuids:
                raise exceptions.ParseError(f"No results_uuids matched to sampling_feature '{sampling_feature.sampling_feature_uuid}'")

            result_values = [] # values for all times
            latest_values = [] # values for only the latest time (i.e. last)
            for key, values in measurement_data.items():
                try:
                    result_id = result_uuids[key]
                except KeyError:
                    continue

                for vi, value in enumerate(values):
                    result_values.append(TimeseriesResultValueTechDebt(
                        result_id=result_id,
                        data_value=value,
                        value_datetime=measurement_datetimes[vi][0],
                        utc_offset=measurement_datetimes[vi][1],
                        censor_code='Not censored',
                        quality_code='None',
                        time_aggregation_interval=1,
                        time_aggregation_interval_unit=unit_id
                    ))
                # nab latest value as that was the one we (by assumption)
                # generated last in the loop
                latest_values.append(result_values[-1])

            # assume the last measurement datetime is the latest
            set_deployment_date(sampling_feature.sampling_feature_id, measurement_datetimes[-1][0], connection)

            insert_timeseries_result_values(result_values, connection)
            update_sensormeasurements(latest_values, connection)
            sync_result_table(latest_values, num_measurements, connection)
           
        return Response({}, status.HTTP_201_CREATED)


#######################################################
### Temporary HOT fix to address model performance
#######################################################
# PRT - the code in this block is meant as a hot fix to address poor model performance
# the long term goal is to refactor the application models to make them more performant.

def get_result_UUIDs(sampling_feature_id:str, connection) -> Union[Dict[str, str],None]:
    try:
        query = text("SELECT r.resultuuid, r.resultid FROM odm2.results AS r " \
                    "JOIN odm2.featureactions AS fa ON r.featureactionid = fa.featureactionid "\
                    "WHERE fa.samplingfeatureid = ':sampling_feature_id';")
        result = connection.execute(query, sampling_feature_id=sampling_feature_id)
        return {str(ruuid): rid for ruuid, rid in result}
    except:
        return None

class TimeseriesResultValueTechDebt():
    def __init__(self, 
            result_id:str,
            data_value:float, 
            value_datetime:datetime, 
            utc_offset:int, 
            censor_code:str,
            quality_code:str, 
            time_aggregation_interval:int, 
            time_aggregation_interval_unit:int) -> None:
        self.result_id = result_id
        self.data_value = data_value
        self.utc_offset = utc_offset
        self.value_datetime = value_datetime
        self.censor_code = censor_code
        self.quality_code = quality_code
        self.time_aggregation_interval = time_aggregation_interval
        self.time_aggregation_interval_unit = time_aggregation_interval_unit

#dataloader utility function
def update_sensormeasurements(result_values:TimeseriesResultValueTechDebt, connection) -> None:
    query = text('INSERT INTO public.dataloaderinterface_sensormeasurement as m '
        'VALUES ((select id from public.dataloaderinterface_sitesensor '
        'where "ResultID" = :result_id limit 1), :datetime, :utc_offset, :data_value) '
        'on conflict (sensor_id) do update set '
        'value_datetime = excluded.value_datetime, '
        'value_datetime_utc_offset = excluded.value_datetime_utc_offset, '
        'data_value = excluded.data_value '
        'where m.value_datetime < excluded.value_datetime;')
    result = connection.execute(query, 
        [{
            "result_id": result_value.result_id,
            "datetime": result_value.value_datetime,
            "utc_offset": timedelta(hours=result_value.utc_offset),
            "data_value": result_value.data_value,
        } for result_value in result_values]
    )

#dataloader utility function
def set_deployment_date(sample_feature_id:int, date_time:datetime, connection) -> None:
    query = text('UPDATE public.dataloaderinterface_siteregistration '\
        'SET "DeploymentDate"=:date_time '\
        'WHERE "DeploymentDate" IS NULL AND ' \
        '"SamplingFeatureID"=:sample_feature_id'                )
    result = connection.execute(query, 
        sample_feature_id=sample_feature_id,
        date_time=date_time
        )
    return None


def sync_result_table(result_values: TimeseriesResultValueTechDebt, num_measurements, connection) -> None:
    query = text("UPDATE odm2.results SET valuecount = valuecount + :num_measurements, " \
        "resultdatetime = GREATEST(:result_datetime, resultdatetime)" \
        "WHERE resultid=:result_id; ")
    result = connection.execute(query, 
        [{
            "result_id": result_value.result_id,
            "result_datetime": result_value.value_datetime,
            "num_measurements": num_measurements,
        } for result_value in result_values]
    )
    return result

def insert_timeseries_result_values(result_values : TimeseriesResultValueTechDebt, connection=None) -> None:
    try:
        query = text("INSERT INTO odm2.timeseriesresultvalues " \
            "(resultid, datavalue, valuedatetime, valuedatetimeutcoffset, " \
            "censorcodecv, qualitycodecv, timeaggregationinterval, timeaggregationintervalunitsid) " \
            "VALUES ( " \
                ":result_id, " \
                ":data_value, " \
                ":value_datetime, " \
                ":utc_offset, " \
                ":censor_code, " \
                ":quality_code, " \
                ":time_aggregation_interval, " \
                ":time_aggregation_interval_unit) on conflict do nothing;")
        result = connection.execute(query,
            [vars(v) for v in result_values]
        )
        return None
    except Exception as e:
        return f"Failed to INSERT data for uuid('{result_value.result_uuid}')"


class Organizations(APIView):
    def get(self, request: HttpRequest) -> Response:
        query = sqlalchemy.text(
            "SELECT organizationid, organizationcode, organizationname FROM odm2.organizations ORDER BY organizationname;"
        )
        with _db_engine.connect() as connection:
            df = pd.read_sql(query, connection)
            data_dict = df.to_dict(orient="records")
            return Response(data_dict, status.HTTP_200_OK)
