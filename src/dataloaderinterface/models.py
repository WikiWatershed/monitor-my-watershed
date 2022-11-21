from __future__ import unicode_literals

# Create your models here.

from datetime import timedelta, datetime
from uuid import uuid4

from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from dataloader.models import SamplingFeature, Affiliation, Result, TimeSeriesResultValue, EquipmentModel, Variable, \
    Unit, Medium, Organization
from dataloaderinterface.querysets import SiteRegistrationQuerySet, SensorOutputQuerySet



#TODO: replace with a different model approach as this has been deprecated
import cognito.models

class SiteRegistration(models.Model):
    registration_id = models.AutoField(primary_key=True, db_column='RegistrationID')
    registration_token = models.CharField(max_length=64, editable=False, db_column='RegistrationToken', unique=True, default=uuid4)

    registration_date = models.DateTimeField(db_column='RegistrationDate', default=datetime.utcnow)
    deployment_date = models.DateTimeField(db_column='DeploymentDate', blank=True, null=True)

    account_id = models.ForeignKey(cognito.models.Account, on_delete=models.CASCADE, db_column='User', related_name='deployed_sites')
    affiliation_id = models.IntegerField(db_column='AffiliationID')

    person_id = models.IntegerField(db_column='PersonID', null=True)
    person_first_name = models.CharField(max_length=255, db_column='PersonFirstName', blank=True, null=True)
    person_last_name = models.CharField(max_length=255, db_column='PersonLastName', blank=True, null=True)

    organization_id = models.IntegerField(db_column='OrganizationID', null=True)
    organization_code = models.CharField(db_column='OrganizationCode', max_length=50, blank=True, null=True)
    organization_name = models.CharField(max_length=255, db_column='OrganizationName', blank=True, null=True)

    sampling_feature_id = models.IntegerField(db_column='SamplingFeatureID', null=True)
    sampling_feature_code = models.CharField(max_length=50, unique=True, db_column='SamplingFeatureCode')
    sampling_feature_name = models.CharField(max_length=255, db_column='SamplingFeatureName')
    elevation_m = models.FloatField(blank=True, null=True, db_column='Elevation')
    elevation_datum = models.CharField(max_length=255, db_column='ElevationDatum', blank=True, null=True)

    latitude = models.FloatField(db_column='Latitude')
    longitude = models.FloatField(db_column='Longitude')
    site_type = models.CharField(max_length=255, db_column='SiteType')

    stream_name = models.CharField(max_length=255, db_column='StreamName', blank=True, null=True)
    major_watershed = models.CharField(max_length=255, db_column='MajorWatershed', blank=True, null=True)
    sub_basin = models.CharField(max_length=255, db_column='SubBasin', blank=True, null=True)
    closest_town = models.CharField(max_length=255, db_column='ClosestTown', blank=True, null=True)

    site_notes = models.TextField(db_column='SiteNotes', blank=True, null=True)

    #TODO: VERIFY THIS BEHAVIOR
    followed_by = models.ManyToManyField(cognito.models.Account, related_name='followed_sites')
    alert_listeners = models.ManyToManyField(cognito.models.Account, related_name='+', through='SiteAlert')

    objects = SiteRegistrationQuerySet.as_manager()

    @property
    def latest_measurement(self):
        if not hasattr(self, 'latest_measurement_id'):
            return
        try:
            last_updated_sensor = [sensor for sensor in self.sensors.all() if sensor.last_measurement.pk == self.latest_measurement_id].pop()
        #except IndexError:
        except:
            return None

        return last_updated_sensor.last_measurement

    @property
    def organization(self):
        return Organization.objects.filter(organization_id=self.organization_id).first()

    @property
    def sampling_feature(self):
        try:
            return SamplingFeature.objects.get(pk=self.sampling_feature_id)
        except ObjectDoesNotExist:
            return None

    @property
    def odm2_affiliation(self):
        try:
            return Affiliation.objects.get(pk=self.affiliation_id)
        except ObjectDoesNotExist:
            return None

    def __str__(self):
        return '%s' % self.sampling_feature_code

    def __repr__(self):
        return "<SiteRegistration('%s', '%s', '%s')>" % (
            self.registration_id, self.registration_date, self.sampling_feature_code
        )


class SensorMeasurement(models.Model):
    sensor = models.OneToOneField('SiteSensor', related_name='last_measurement', on_delete=models.CASCADE, primary_key=True)
    value_datetime = models.DateTimeField()
    value_datetime_utc_offset = models.DurationField()
    data_value = models.FloatField()

    @property
    def value_local_datetime(self):
        return self.value_datetime + self.value_datetime_utc_offset

    @property
    def utc_offset_hours_display(self):
        total = int(self.value_datetime_utc_offset.total_seconds() / 3600)
        return "(UTC{sign}{hours}:00)".format(sign=["-", "+"][total > 0], hours=str(abs(self.utc_offset_hours)).zfill(2))

    @property
    def utc_offset_hours(self):
        return int(self.value_datetime_utc_offset.total_seconds() / 3600)

    def __str__(self):
        return '%s: %s' % (self.value_datetime, self.data_value)

    def __repr__(self):
        return "<SensorMeasurement('%s', %s, '%s', '%s')>" % (
            self.sensor, self.value_datetime, self.value_datetime_utc_offset, self.data_value
        )


class SensorOutput(models.Model):
    instrument_output_variable_id = models.IntegerField(db_index=True)

    model_id = models.IntegerField()
    model_name = models.CharField(max_length=255)
    model_manufacturer = models.CharField(max_length=255)

    variable_id = models.IntegerField()
    variable_name = models.CharField(max_length=255)
    variable_code = models.CharField(max_length=50)

    unit_id = models.IntegerField()
    unit_name = models.CharField(max_length=255)
    unit_abbreviation = models.CharField(max_length=255)

    sampled_medium = models.CharField(max_length=255, null=True)

    objects = SensorOutputQuerySet.as_manager()

    @property
    def variable(self):
        return Variable.objects.filter(variable_id=self.variable_id).first()

    @property
    def unit(self):
        return Unit.objects.filter(unit_id=self.unit_id).first()

    def __str__(self):
        return '%s %s %s %s %s' % (self.model_manufacturer, self.model_name, self.variable_code, self.unit_name, self.sampled_medium)

    def __repr__(self):
        return "<SensorOutput('%s', [%s], ['%s'], ['%s'], ['%s'])>" % (
            self.pk, self.model_name, self.variable_code, self.unit_name, self.sampled_medium
        )


class SiteSensor(models.Model):
    registration = models.ForeignKey('SiteRegistration', db_column='RegistrationID', on_delete=models.CASCADE, related_name='sensors')

    result_id = models.IntegerField(db_column='ResultID', unique=True, null=True)
    result_uuid = models.UUIDField(db_column='ResultUUID', unique=True, null=True)

    height = models.FloatField(blank=True, null=True)
    sensor_notes = models.TextField(blank=True, null=True)
    sensor_output = models.ForeignKey('SensorOutput', related_name='sensor_instances', on_delete=models.CASCADE, null=True)

    class Meta:
        ordering = ['result_id']

    @property
    def result(self):
        return Result.objects.filter(pk=self.result_id).first()

    @property
    def make_model(self):
        return "{0}_{1}".format(self.sensor_output.model_manufacturer, self.sensor_output.model_name)

    @property
    def sensor_identity(self):
        return "{0}_{1}_{2}".format(self.registration.sampling_feature_code, self.sensor_output.variable_code, self.result_id)

    def __str__(self):
        return '%s' % (self.sensor_identity)

    def __repr__(self):
        return "<SiteSensor('%s', [%s], '%s')>" % (
            self.id, self.registration, self.result_id
        )


class SiteAlert(models.Model):
    user = models.ForeignKey(cognito.models.Account ,db_column='User', on_delete=models.CASCADE, related_name='site_alerts')
    site_registration = models.ForeignKey('SiteRegistration', db_column='RegistrationID', on_delete=models.CASCADE, related_name='alerts')
    last_alerted = models.DateTimeField(db_column='LastAlerted', blank=True, null=True)
    hours_threshold = models.DurationField(db_column='HoursThreshold', default=timedelta(hours=1))

    def __str__(self):
        return '%s %s' % (self.site_registration.sampling_feature_code, self.hours_threshold)

    def __repr__(self):
        return "<SiteAlert('%s', [%s], '%s', '%s')>" % (
            self.id, self.site_registration.sampling_feature_code, self.last_alerted, self.hours_threshold,
        )