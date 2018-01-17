from __future__ import unicode_literals

# Create your models here.
import uuid

from django.db.models.aggregates import Min, Max

from dataloader.models import SamplingFeature, Affiliation, Result, TimeSeriesResultValue, EquipmentModel, Variable, \
    Unit, Medium
from django.contrib.auth.models import User
from django.db import models

from django.conf import settings


class SiteRegistration(models.Model):
    registration_id = models.AutoField(primary_key=True, db_column='RegistrationID')
    registration_token = models.CharField(max_length=64, editable=False, db_column='RegistrationToken', unique=True)

    registration_date = models.DateTimeField(db_column='RegistrationDate')
    deployment_date = models.DateTimeField(db_column='DeploymentDate', blank=True, null=True)

    django_user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='User', related_name='registrations')
    affiliation_id = models.IntegerField(db_column='AffiliationID')
    person = models.CharField(max_length=765, db_column='Person')
    organization = models.CharField(max_length=255, db_column='Organization', blank=True, null=True)

    sampling_feature_id = models.IntegerField(db_column='SamplingFeatureID')
    sampling_feature_code = models.CharField(max_length=50, unique=True, db_column='SamplingFeatureCode')
    sampling_feature_name = models.CharField(max_length=255, blank=True, db_column='SamplingFeatureName')
    elevation_m = models.FloatField(blank=True, null=True, db_column='Elevation')

    latitude = models.FloatField(db_column='Latitude')
    longitude = models.FloatField(db_column='Longitude')
    site_type = models.CharField(max_length=765, db_column='SiteType')

    followed_by = models.ManyToManyField(User, related_name='followed_sites')
    alert_listeners = models.ManyToManyField(User, related_name='+', through='SiteAlert')

    @property
    def sampling_feature(self):
        return SamplingFeature.objects.get(pk=self.sampling_feature_id)

    @property
    def odm2_affiliation(self):
        return Affiliation.objects.get(pk=self.affiliation_id)


    def __str__(self):
        return '%s by %s from %s on %s' % (self.sampling_feature_code, self.person, self.organization, self.registration_date)

    def __repr__(self):
        return "<SiteRegistration('%s', '%s', '%s', '%s')>" % (
            self.registration_id, self.registration_date, self.sampling_feature_code, self.person
        )


class SiteSensor(models.Model):
    registration = models.ForeignKey('SiteRegistration', db_column='RegistrationID', related_name='sensors')

    result_id = models.IntegerField(db_column='ResultID', unique=True)
    result_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_column='ResultUUID', unique=True)

    model_name = models.CharField(db_column='ModelName', max_length=255)
    model_manufacturer = models.CharField(db_column='ModelManufacturer', max_length=255)

    variable_name = models.CharField(max_length=255, db_column='VariableName')
    variable_code = models.CharField(max_length=50, db_column='VariableCode')

    unit_name = models.CharField(max_length=255, db_column='UnitsName')
    unit_abbreviation = models.CharField(max_length=255, db_column='UnitAbbreviation')

    sampled_medium = models.CharField(db_column='SampledMedium', max_length=255)

    last_measurement_id = models.IntegerField(db_column='LastMeasurementID', unique=True, blank=True, null=True)
    last_measurement_value = models.FloatField(db_column='LastMeasurementValue', blank=True, null=True)
    last_measurement_datetime = models.DateTimeField(db_column='LastMeasurementDatetime', blank=True, null=True)
    last_measurement_utc_offset = models.IntegerField(db_column='LastMeasurementUtcOffset', blank=True, null=True)
    last_measurement_utc_datetime = models.DateTimeField(db_column='LastMeasurementUtcDatetime', blank=True, null=True)

    activation_date = models.DateTimeField(db_column='ActivationDate', blank=True, null=True)
    activation_date_utc_offset = models.IntegerField(db_column='ActivationDateUtcOffset', blank=True, null=True)

    class Meta:
        ordering = ['result_id']

    @property
    def result(self):
        return Result.objects.get(pk=self.result_id)

    @property
    def equipment_model(self):
        return EquipmentModel.objects.filter(model_name=self.model_name).first()

    @property
    def variable(self):
        return Variable.objects.filter(variable_code=self.variable_code).first()

    @property
    def unit(self):
        return Unit.objects.filter(unit_name=self.unit_name).first()

    @property
    def medium(self):
        return Medium.objects.filter(name=self.sampled_medium).first()

    @property
    def make_model(self):
        return "{0}_{1}".format(self.model_manufacturer, self.model_name)

    @property
    def last_measurement(self):
        return TimeSeriesResultValue.objects.filter(pk=self.last_measurement_id).first()

    @property
    def sensor_identity(self):
        return "{0}_{1}_{2}".format(self.registration.sampling_feature_code, self.variable_code, self.result_id)

    @property
    def influx_url(self):
        if not self.last_measurement_id:
            return

        return settings.INFLUX_URL_QUERY.format(
            result_uuid=str(self.result_uuid).replace('-', '_'),
            last_measurement=self.last_measurement_datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
            days_of_data=settings.SENSOR_DATA_PERIOD
        )

    def __str__(self):
        return '%s %s' % (self.variable_name, self.unit_abbreviation)

    def __repr__(self):
        return "<SiteSensor('%s', [%s], '%s', '%s')>" % (
            self.id, self.registration, self.variable_code, self.unit_abbreviation,
        )


class ODM2User(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    affiliation_id = models.IntegerField()

    @property
    def affiliation(self):
        return Affiliation.objects.get(pk=self.affiliation_id)

    def can_administer_site(self, registration):
        return self.user.is_staff or registration.user == self


class SiteAlert(models.Model):
    user = models.ForeignKey(User, db_column='User', related_name='site_alerts')
    site_registration = models.ForeignKey('SiteRegistration', db_column='RegistrationID', related_name='alerts')
    last_alerted = models.DateTimeField(db_column='LastAlerted', blank=True, null=True)
    hours_threshold = models.PositiveIntegerField(db_column='HoursThreshold', default=15)

    def __str__(self):
        return '%s %s' % (self.site_registration.sampling_feature_code, self.hours_threshold)

    def __repr__(self):
        return "<SiteAlert('%s', [%s], '%s', '%s')>" % (
            self.id, self.site_registration.sampling_feature_code, self.last_alerted, self.hours_threshold,
        )
