# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

from django.db import models
from django.utils.six import python_2_unicode_compatible


@python_2_unicode_compatible
class DataSeries(models.Model):
    series_id = models.AutoField(db_column='SeriesID', primary_key=True)
    result_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_column='ResultUUID', unique=True)
    influx_identifier = models.TextField(db_column='InfluxIdentifier')
    source_data_service_id = models.IntegerField(db_column='SourceDataServiceID')
    network = models.CharField(db_column='Network', max_length=50)
    site_code = models.CharField(db_column='SiteCode', max_length=50)
    site_name = models.CharField(db_column='SiteName', max_length=500)
    latitude = models.FloatField(db_column='Latitude', null=True, blank=True)
    longitude = models.FloatField(db_column='Longitude', null=True, blank=True)
    state = models.CharField(db_column='State', max_length=50, null=True, blank=True)
    county = models.CharField(db_column='County', max_length=50, null=True, blank=True)
    site_type = models.CharField(db_column='SiteType', max_length=50)
    variable_code = models.CharField(db_column='VariableCode', max_length=50)
    variable_name = models.CharField(db_column='VariableName', max_length=255)
    variable_level = models.CharField(db_column='VariableLevel', max_length=50)
    method_description = models.CharField(db_column='MethodDescription', max_length=500)
    variable_units_name = models.CharField(db_column='VariableUnitsName', max_length=255, null=True, blank=True)
    variable_units_type = models.CharField(db_column='VariableUnitsType', max_length=50, null=True, blank=True)
    variable_units_abbreviation = models.CharField(db_column='VariableUnitsAbbreviation', max_length=50)
    sample_medium = models.CharField(db_column='SampleMedium', max_length=50)
    value_type = models.CharField(db_column='ValueType', max_length=50, null=True, blank=True)
    data_type = models.CharField(db_column='DataType', max_length=50, null=True, blank=True)
    general_category = models.CharField(db_column='GeneralCategory', max_length=50, null=True, blank=True)
    time_support = models.FloatField(db_column='TimeSupport', null=True, blank=True)
    time_support_unit_sname = models.CharField(db_column='TimeSupportUnitsName', max_length=500, null=True, blank=True)
    time_support_units_type = models.CharField(db_column='TimeSupportUnitsType', max_length=50, null=True, blank=True)
    time_support_units_abbreviation = models.CharField(db_column='TimeSupportUnitsAbbreviation', max_length=50, null=True, blank=True)
    quality_control_level_code = models.CharField(db_column='QualityControlLevelCode', max_length=50, null=True, blank=True)
    quality_control_level_definition = models.CharField(db_column='QualityControlLevelDefinition', max_length=500)
    quality_control_level_explanation = models.CharField(db_column='QualityControlLevelExplanation', max_length=500, null=True, blank=True)
    source_organization = models.CharField(db_column='SourceOrganization', max_length=255)
    source_description = models.CharField(db_column='SourceDescription', max_length=500, blank=True, null=True)
    begin_datetime = models.DateTimeField(db_column='BeginDateTime')
    end_datetime = models.DateTimeField(db_column='EndDateTime', blank=True, null=True)
    utc_offset = models.IntegerField(db_column='UTCOffset', null=True, blank=True)
    number_observations = models.IntegerField(db_column='NumberObservations')
    date_last_updated = models.DateTimeField(db_column='DateLastUpdated', blank=True, null=True)
    is_active = models.BigIntegerField(db_column='IsActive')
    get_data_url = models.CharField(db_column='GetDataURL', max_length=500)
    get_data_influx = models.TextField(db_column='GetDataInflux')
    no_data_value = models.BigIntegerField(db_column='NoDataValue', default=-9999)

    def __str__(self):
        return "{} {} - {}".format(self.site_code, self.variable_code, self.result_uuid)

    class Meta:
        managed = False
        db_table = 'DataSeries'