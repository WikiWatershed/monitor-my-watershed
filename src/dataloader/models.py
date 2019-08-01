from __future__ import unicode_literals

import inspect
import sys
import uuid

from dataloader.querysets import AffiliationQuerySet, RelatedActionManager, ResultManager, \
    DataLoggerFileManager, InstrumentOutputVariableManager, \
    EquipmentManager, CalibrationReferenceEquipmentManager, EquipmentUsedManager, MaintenanceActionManager, \
    RelatedEquipmentManager, CalibrationActionManager, ODM2QuerySet, ActionQuerySet, ActionByQuerySet, \
    FeatureActionQuerySet, TimeSeriesValuesQuerySet, EquipmentModelQuerySet, OrganizationQuerySet
from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


# TODO: function to handle the file upload folder for file fields.


# region Model Abstractions


class ODM2Model(models.Model):
    objects = ODM2QuerySet.as_manager()

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ControlledVocabulary(ODM2Model):
    term = models.CharField(db_column='term', max_length=255)
    name = models.CharField(db_column='name', primary_key=True, max_length=255)
    definition = models.CharField(db_column='definition', blank=True, max_length=500)
    category = models.CharField(db_column='category', blank=True, max_length=255)
    source_vocabulary_uri = models.CharField(db_column='sourcevocabularyuri', blank=True, max_length=255)

    def __str__(self):
        return '%s' % self.name

    def __repr__(self):
        return "<%s('%s', '%s', '%s', '%s')>" % (
            self.__class__.__name__, self.term, self.name, self.definition, self.category
        )

    class Meta:
        abstract = True


@python_2_unicode_compatible
class AnnotationBridge(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    annotation = models.ForeignKey('Annotation', db_column='annotationid')

    def __str__(self):
        return '%s' % self.annotation

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ExtensionPropertyBridge(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    property = models.ForeignKey('ExtensionProperty', db_column='propertyid')
    property_value = models.CharField(db_column='propertyvalue', max_length=255)

    def __str__(self):
        return '%s %s' % self.annotation, self.property_value

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ExternalIdentifierBridge(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    external_identifier_system = models.ForeignKey('ExternalIdentifierSystem', db_column='externalidentifiersystemid')

    def __str__(self):
        return '%s' % self.external_identifier_system

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ObjectRelation(models.Model):
    relation_id = models.AutoField(db_column='relationid', primary_key=True)
    relationship_type = models.ForeignKey('RelationshipType', db_column='relationshiptypecv')

    def __str__(self):
        return '%s' % self.relationship_type_id

    class Meta:
        abstract = True

# region Result Abstractions


@python_2_unicode_compatible
class ExtendedResult(models.Model):
    result = models.OneToOneField('Result', db_column='resultid', primary_key=True)
    spatial_reference = models.ForeignKey('SpatialReference', db_column='spatialreferenceid', blank=True, null=True)

    def __str__(self):
        return '%s' % self.result

    def __repr__(self):
        return "<%s('%s', '%s', SpatialReference['%s', '%s'])>" % (
            self.__class__.__name__, self.result_id, self.result, self.spatial_reference_id, self.spatial_reference
        )

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ResultValue(models.Model):
    value_id = models.BigAutoField(db_column='valueid', primary_key=True)
    value_datetime = models.DateTimeField(db_column='valuedatetime')
    value_datetime_utc_offset = models.IntegerField(db_column='valuedatetimeutcoffset')

    def __str__(self):
        return '%s %s' % (self.value_datetime, self.data_value)

    def __repr__(self):
        return "<%s('%s', '%s', Result['%s', '%s'], '%s')>" % (
            self.__class__.__name__, self.value_id, self.value_datetime, self.result_id, self.result, self.data_value
        )

    class Meta:
        abstract = True


@python_2_unicode_compatible
class ResultValueAnnotation(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    annotation = models.ForeignKey('Annotation', db_column='annotationid')

    def __str__(self):
        return '%s %s' % (self.value_datetime, self.data_value)

    def __repr__(self):
        return "<%s('%s', Annotation['%s', '%s'], ResultValue['%s', '%s')>" % (
            self.__class__.__name__, self.bridge_id, self.annotation_id, self.annotation, self.value_id, self.value
        )

    class Meta:
        abstract = True


class AggregatedComponent(models.Model):
    aggregation_statistic = models.ForeignKey('AggregationStatistic', db_column='aggregationstatisticcv')

    class Meta:
        abstract = True


class TimeAggregationComponent(models.Model):
    time_aggregation_interval = models.FloatField(db_column='timeaggregationinterval')
    time_aggregation_interval_unit = models.ForeignKey('Unit', related_name='+', db_column='timeaggregationintervalunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class XOffsetComponent(models.Model):
    x_location = models.FloatField(db_column='xlocation')
    x_location_unit = models.ForeignKey('Unit', related_name='+', db_column='xlocationunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class YOffsetComponent(models.Model):
    y_location = models.FloatField(db_column='ylocation')
    y_location_unit = models.ForeignKey('Unit', related_name='+', db_column='ylocationunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class ZOffsetComponent(models.Model):
    z_location = models.FloatField(db_column='zlocation')
    z_location_unit = models.ForeignKey('Unit', related_name='+', db_column='zlocationunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class XIntendedComponent(models.Model):
    intended_x_spacing = models.FloatField(db_column='intendedxspacing')
    intended_x_spacing_unit = models.ForeignKey('Unit', related_name='+', db_column='intendedxspacingunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class YIntendedComponent(models.Model):
    intended_y_spacing = models.FloatField(db_column='intendedyspacing', blank=True, null=True)
    intended_y_spacing_unit = models.ForeignKey('Unit', related_name='+', db_column='intendedyspacingunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class ZIntendedComponent(models.Model):
    intended_z_spacing = models.FloatField(db_column='intendedzspacing', blank=True, null=True)
    intended_z_spacing_unit = models.ForeignKey('Unit', related_name='+', db_column='intendedzspacingunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class TimeIntendedComponent(models.Model):
    intended_time_spacing = models.FloatField(db_column='intendedtimespacing', blank=True, null=True)
    intended_time_spacing_unit = models.ForeignKey('Unit', related_name='+', db_column='intendedtimespacingunitsid', blank=True, null=True)

    class Meta:
        abstract = True


class QualityControlComponent(models.Model):
    censor_code = models.ForeignKey('CensorCode', db_column='censorcodecv')
    quality_code = models.ForeignKey('QualityCode', db_column='qualitycodecv')

    class Meta:
        abstract = True


# endregion

# endregion

# region ODM2 Controlled Vocabulary models


class ActionType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_actiontype'


class AggregationStatistic(ControlledVocabulary):
    class Meta:
        db_table = 'cv_aggregationstatistic'


class AnnotationType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_annotationtype'


class CensorCode(ControlledVocabulary):
    class Meta:
        db_table = 'cv_censorcode'


class DataQualityType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_dataqualitytype'


class DataSetType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_datasettype'


class DeploymentType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_deploymenttype'


class DirectiveType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_directivetype'


class ElevationDatum(ControlledVocabulary):
    class Meta:
        db_table = 'cv_elevationdatum'
        ordering = ['name']


class EquipmentType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_equipmenttype'


class Medium(ControlledVocabulary):
    class Meta:
        db_table = 'cv_medium'
        ordering = ['name']


class MethodType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_methodtype'
        ordering = ['name']


class OrganizationType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_organizationtype'
        ordering = ['name']


class PropertyDataType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_propertydatatype'


class QualityCode(ControlledVocabulary):
    class Meta:
        db_table = 'cv_qualitycode'


class ResultType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_resulttype'


class RelationshipType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_relationshiptype'


class SamplingFeatureGeoType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_samplingfeaturegeotype'


class SamplingFeatureType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_samplingfeaturetype'


class SpatialOffsetType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_spatialoffsettype'


class Speciation(ControlledVocabulary):
    class Meta:
        db_table = 'cv_speciation'


class SpecimenType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_specimentype'


class SiteType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_sitetype'
        ordering = ['name']


class Status(ControlledVocabulary):
    class Meta:
        db_table = 'cv_status'


class TaxonomicClassifierType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_taxonomicclassifiertype'


class UnitsType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_unitstype'
        ordering = ['name']


class VariableName(ControlledVocabulary):
    class Meta:
        db_table = 'cv_variablename'
        ordering = ['name']


class VariableType(ControlledVocabulary):
    class Meta:
        db_table = 'cv_variabletype'
        ordering = ['name']


class ReferenceMaterialMedium(ControlledVocabulary):
    class Meta:
        db_table = 'cv_referencematerialmedium'

# endregion

# region ODM2 Core models


@python_2_unicode_compatible
class People(ODM2Model):
    person_id = models.AutoField(db_column='personid', primary_key=True)
    person_first_name = models.CharField(db_column='personfirstname', max_length=255)
    person_middle_name = models.CharField(db_column='personmiddlename', blank=True, max_length=255)
    person_last_name = models.CharField(db_column='personlastname', max_length=255)

    citations = models.ManyToManyField('Citation', related_name='cited_authors', through='AuthorList')
    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='people',
                                                  through='PersonExternalIdentifier')

    def __str__(self):
        return '%s %s' % (self.person_first_name, self.person_last_name)

    def __repr__(self):
        return "<Person('%s', '%s', '%s')>" % (
            self.person_id, self.person_first_name, self.person_last_name
        )

    class Meta:
        db_table = 'people'
        ordering = ['person_first_name', 'person_last_name']


@python_2_unicode_compatible
class Organization(ODM2Model):
    organization_id = models.AutoField(db_column='organizationid', primary_key=True)
    organization_type = models.ForeignKey('OrganizationType', db_column='organizationtypecv')
    organization_code = models.CharField(db_column='organizationcode', max_length=50, unique=True)
    organization_name = models.CharField(db_column='organizationname', max_length=255)
    organization_description = models.CharField(db_column='organizationdescription', blank=True, max_length=500)
    organization_link = models.CharField(db_column='organizationlink', blank=True, max_length=255)
    parent_organization = models.ForeignKey('self', db_column='parentorganizationid', blank=True, null=True)

    people = models.ManyToManyField('People', through='Affiliation')

    objects = OrganizationQuerySet.as_manager()

    def __str__(self):
        return '%s' % self.organization_code

    def __repr__(self):
        return "<Organization('%s', '%s', '%s', '%s')>" % (
            self.organization_id, self.organization_type_id, self.organization_code, self.organization_name
        )

    class Meta:
        db_table = 'organizations'
        ordering = ['organization_code']


@python_2_unicode_compatible
class Affiliation(ODM2Model):
    affiliation_id = models.AutoField(db_column='affiliationid', primary_key=True)
    person = models.ForeignKey('People', related_name='affiliations', db_column='personid')
    organization = models.ForeignKey('Organization', related_name='affiliations', db_column='organizationid', blank=True, null=True)
    is_primary_organization_contact = models.NullBooleanField(db_column='isprimaryorganizationcontact', default=None)
    affiliation_start_date = models.DateField(db_column='affiliationstartdate')
    affiliation_end_date = models.DateField(db_column='affiliationenddate', blank=True, null=True)
    primary_phone = models.CharField(db_column='primaryphone', blank=True, max_length=50)
    primary_email = models.CharField(db_column='primaryemail', max_length=255)
    primary_address = models.CharField(db_column='primaryaddress', blank=True, max_length=255)
    person_link = models.CharField(db_column='personlink', blank=True, max_length=255)

    objects = AffiliationQuerySet.as_manager()

    @property
    def role_status(self):
        return 'Primary contact' if self.is_primary_organization_contact else 'Secondary contact'

    def __str__(self):
        return '%s - %s' % (self.person, self.organization)

    def __repr__(self):
        return "<Affiliation('%s', Person['%s', '%s'], Organization['%s', '%s'], '%s', '%s', '%s')>" % (
            self.affiliation_id, self.person_id, self.person, self.organization_id, self.organization,
            self.role_status, self.primary_email, self.primary_address
        )

    class Meta:
        db_table = 'affiliations'
        ordering = ['person__person_first_name', 'person__person_last_name']


@python_2_unicode_compatible
class Method(ODM2Model):
    method_id = models.AutoField(db_column='methodid', primary_key=True)
    method_type = models.ForeignKey('MethodType', db_column='methodtypecv')
    method_code = models.CharField(db_column='methodcode', max_length=50)
    method_name = models.CharField(db_column='methodname', max_length=255)
    method_description = models.CharField(db_column='methoddescription', blank=True, max_length=500)
    method_link = models.CharField(db_column='methodlink', blank=True, max_length=255)
    organization = models.ForeignKey('Organization', db_column='organizationid', blank=True, null=True)

    annotations = models.ManyToManyField('Annotation', related_name='annotated_methods', through='MethodAnnotation')
    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='methods', through='MethodExtensionPropertyValue')
    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='methods', through='MethodExternalIdentifier')

    def __str__(self):
        return '%s (%s)' % (self.method_name, self.method_type_id)

    def __repr__(self):
        return "<Method('%s', '%s', '%s', '%s', '%s', '%s')>" % (
            self.method_id, self.method_type_id, self.method_code,
            self.method_name, self.method_description, self.method_link
        )

    class Meta:
        db_table = 'methods'


@python_2_unicode_compatible
class Action(ODM2Model):
    action_id = models.AutoField(db_column='actionid', primary_key=True)
    action_type = models.ForeignKey('ActionType', db_column='actiontypecv')
    method = models.ForeignKey('Method', db_column='methodid')
    begin_datetime = models.DateTimeField(db_column='begindatetime')
    begin_datetime_utc_offset = models.IntegerField(db_column='begindatetimeutcoffset')
    end_datetime = models.DateTimeField(db_column='enddatetime', blank=True, null=True)
    end_datetime_utc_offset = models.IntegerField(db_column='enddatetimeutcoffset', blank=True, null=True)
    action_description = models.TextField(db_column='actiondescription', blank=True)
    action_file_link = models.FileField(db_column='actionfilelink', blank=True)

    people = models.ManyToManyField('Affiliation', related_name='actions', through='ActionBy')
    equipment_used = models.ManyToManyField('Equipment', related_name='actions', through='EquipmentUsed')
    directives = models.ManyToManyField('Directive', related_name='actions', through='ActionDirective')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_actions', through='ActionAnnotation')
    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='actions', through='ActionExtensionPropertyValue')

    objects = ActionQuerySet.as_manager()

    def __str__(self):
        return '%s %s %s' % (
            self.begin_datetime, self.begin_datetime_utc_offset, self.action_type_id
        )

    def __repr__(self):
        return "<Action('%s', '%s', '%s')>" % (
            self.action_id, self.action_type_id, self.begin_datetime
        )

    class Meta:
        db_table = 'actions'


@python_2_unicode_compatible
class ActionBy(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    action = models.ForeignKey('Action', related_name="action_by", db_column='actionid')
    affiliation = models.ForeignKey('Affiliation', db_column='affiliationid')
    is_action_lead = models.BooleanField(db_column='isactionlead', default=None)
    role_description = models.CharField(db_column='roledescription', blank=True, max_length=255)

    objects = ActionByQuerySet.as_manager()

    def __str__(self):
        return '%s by %s' % (self.action, self.affiliation)

    def __repr__(self):
        return "<ActionBy('%s', Action['%s', '%s'], Affiliation['%s', '%s'])>" % (
            self.bridge_id, self.action_id, self.action, self.affiliation_id, self.affiliation
        )

    class Meta:
        db_table = 'actionby'


@python_2_unicode_compatible
class SamplingFeature(models.Model):
    sampling_feature_id = models.AutoField(db_column='samplingfeatureid', primary_key=True)
    sampling_feature_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_column='samplingfeatureuuid')
    sampling_feature_type = models.ForeignKey('SamplingFeatureType', db_column='samplingfeaturetypecv')
    sampling_feature_code = models.CharField(db_column='samplingfeaturecode', max_length=50, unique=True)
    sampling_feature_name = models.CharField(db_column='samplingfeaturename', blank=True, max_length=255)
    sampling_feature_description = models.CharField(db_column='samplingfeaturedescription', blank=True, max_length=500)
    sampling_feature_geo_type = models.ForeignKey('SamplingFeatureGeoType', db_column='samplingfeaturegeotypecv', blank=True, null=True)
    elevation_m = models.FloatField(db_column='elevation_m', blank=True, null=True)
    elevation_datum = models.ForeignKey('ElevationDatum', db_column='elevationdatumcv', blank=True, null=True)
    feature_geometry = models.BinaryField(db_column='featuregeometry', blank=True, null=True)

    actions = models.ManyToManyField('Action', related_name='sampling_features', through='FeatureAction')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_sampling_features', through='SamplingFeatureAnnotation')
    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='sampling_features',
                                                       through='SamplingFeatureExtensionPropertyValue')
    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='sampling_features',
                                                  through='SamplingFeatureExternalIdentifier')

    @property
    def latest_updated_result(self):
        return self.feature_actions.with_results()\
            .filter(results__value_count__gt=0)\
            .latest('results__result_datetime').results.first()

    def __str__(self):
        return '%s %s' % (self.sampling_feature_code, self.sampling_feature_name)

    def __repr__(self):
        return "<SamplingFeature('%s', '%s', '%s', '%s', '%s')>" % (
            self.sampling_feature_id, self.sampling_feature_type_id,
            self.sampling_feature_code, self.sampling_feature_name, self.elevation_m
        )

    class Meta:
        db_table = 'samplingfeatures'


@python_2_unicode_compatible
class FeatureAction(models.Model):
    feature_action_id = models.AutoField(db_column='featureactionid', primary_key=True)
    sampling_feature = models.ForeignKey('SamplingFeature', related_name="feature_actions", db_column='samplingfeatureid')
    action = models.ForeignKey('Action', related_name="feature_actions", db_column='actionid')

    objects = FeatureActionQuerySet.as_manager()

    def __str__(self):
        return '%s on %s' % (self.action.action_type_id, self.sampling_feature)

    def __repr__(self):
        return "<FeatureAction('%s', Action['%s', '%s'], SamplingFeature['%s', '%s'])>" % (
            self.feature_action_id, self.action_id, self.action, self.sampling_feature_id, self.sampling_feature
        )

    class Meta:
        db_table = 'featureactions'


@python_2_unicode_compatible
class DataSet(models.Model):
    data_set_id = models.AutoField(db_column='datasetid', primary_key=True)
    data_set_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_column='datasetuuid')
    data_set_type = models.ForeignKey('DataSetType', db_column='datasettypecv')
    data_set_code = models.CharField(db_column='datasetcode', max_length=50)
    data_set_title = models.CharField(db_column='datasettitle', max_length=255)
    data_set_abstract = models.CharField(db_column='datasetabstract', max_length=500)

    citations = models.ManyToManyField('Citation', related_name='cited_data_sets', through='DataSetCitation')

    def __str__(self):
        return '%s %s' % (self.data_set_code, self.data_set_title)

    def __repr__(self):
        return "<DataSet('%s', '%s', '%s', '%s')>" % (
            self.data_set_id, self.data_set_type_id, self.data_set_code, self.data_set_title
        )

    class Meta:
        db_table = 'datasets'


@python_2_unicode_compatible
class ProcessingLevel(models.Model):
    processing_level_id = models.AutoField(db_column='processinglevelid', primary_key=True)
    processing_level_code = models.CharField(db_column='processinglevelcode', max_length=50)
    definition = models.CharField(db_column='definition', blank=True, max_length=500)
    explanation = models.CharField(db_column='explanation', blank=True, max_length=500)

    def __str__(self):
        return '%s (%s)' % (self.processing_level_code, self.definition)

    def __repr__(self):
        return "<ProcessingLevel('%s', '%s', '%s')>" % (
            self.processing_level_id, self.processing_level_code, self.definition
        )

    class Meta:
        db_table = 'processinglevels'


class RelatedAction(ObjectRelation):
    action = models.ForeignKey('Action', related_name='related_actions', db_column='actionid')
    related_action = models.ForeignKey('Action', related_name='reverse_related_actions', db_column='relatedactionid')

    objects = RelatedActionManager()

    def __str__(self):
        return '(%s) %s (%s)' % (self.action, self.relationship_type_id, self.related_action)

    def __repr__(self):
        return "<RelatedAction('%s', Action['%s', '%s'], '%s', Action['%s', '%s'])>" % (
            self.relation_id, self.action_id, self.action, self.relationship_type_id,
            self.related_action_id, self.related_action
        )

    class Meta:
        db_table = 'relatedactions'


@python_2_unicode_compatible
class TaxonomicClassifier(models.Model):
    taxonomic_classifier_id = models.AutoField(db_column='taxonomicclassifierid', primary_key=True)
    taxonomic_classifier_type = models.ForeignKey('TaxonomicClassifierType', db_column='taxonomicclassifiertypecv')
    taxonomic_classifier_name = models.CharField(db_column='taxonomicclassifiername', max_length=255)
    taxonomic_classifier_common_name = models.CharField(db_column='taxonomicclassifiercommonname', blank=True, max_length=255)
    taxonomic_classifier_description = models.CharField(db_column='taxonomicclassifierdescription', blank=True, max_length=500)
    parent_taxonomic_classifier = models.ForeignKey('self', db_column='parenttaxonomicclassifierid', blank=True, null=True)

    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='taxonomic_classifier',
                                                  through='TaxonomicClassifierExternalIdentifier')

    def __str__(self):
        return '%s (%s)' % (self.taxonomic_classifier_common_name, self.taxonomic_classifier_name)

    def __repr__(self):
        return "<TaxonomicClassifier('%s', '%s', '%s', '%s')>" % (
            self.taxonomic_classifier_id, self.taxonomic_classifier_type_id,
            self.taxonomic_classifier_name, self.taxonomic_classifier_common_name
        )

    class Meta:
        db_table = 'taxonomicclassifiers'


@python_2_unicode_compatible
class Unit(models.Model):
    unit_id = models.AutoField(db_column='unitsid', primary_key=True)
    unit_type = models.ForeignKey('UnitsType', db_column='unitstypecv')
    unit_abbreviation = models.CharField(db_column='unitsabbreviation', max_length=255)
    unit_name = models.CharField(db_column='unitsname', max_length=255)
    unit_link = models.CharField(db_column='unitslink', blank=True, max_length=255)

    def __str__(self):
        return '%s - %s (%s)' % (self.unit_name, self.unit_abbreviation, self.unit_type_id)

    def __repr__(self):
        return "<Unit('%s', '%s', '%s', '%s')>" % (
            self.unit_id, self.unit_type_id, self.unit_abbreviation, self.unit_name
        )

    class Meta:
        db_table = 'units'
        ordering = ['unit_name', 'unit_type_id']


@python_2_unicode_compatible
class Variable(models.Model):
    variable_id = models.AutoField(db_column='variableid', primary_key=True)
    variable_type = models.ForeignKey('VariableType', db_column='variabletypecv')
    variable_code = models.CharField(db_column='variablecode', max_length=50)
    variable_name = models.ForeignKey('VariableName', db_column='variablenamecv')
    variable_definition = models.CharField(db_column='variabledefinition', blank=True, max_length=500)
    speciation = models.ForeignKey('Speciation', db_column='speciationcv', blank=True, null=True)
    no_data_value = models.FloatField(db_column='nodatavalue')

    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='variables',
                                                       through='VariableExtensionPropertyValue')
    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='variables',
                                                  through='VariableExternalIdentifier')

    def __str__(self):
        return '%s' % self.variable_code

    def __repr__(self):
        return "<Variable('%s', '%s', '%s', '%s')>" % (
            self.variable_id, self.variable_code, self.variable_name_id, self.variable_type_id
        )

    class Meta:
        db_table = 'variables'
        ordering = ['variable_code']


@python_2_unicode_compatible
class Result(models.Model):
    result_id = models.AutoField(db_column='resultid', primary_key=True)
    result_uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_column='resultuuid')
    feature_action = models.ForeignKey('FeatureAction', related_name='results', db_column='featureactionid')
    result_type = models.ForeignKey('ResultType', db_column='resulttypecv')
    variable = models.ForeignKey('Variable', db_column='variableid')
    unit = models.ForeignKey('Unit', db_column='unitsid')
    taxonomic_classifier = models.ForeignKey('TaxonomicClassifier', db_column='taxonomicclassifierid', blank=True, null=True)
    processing_level = models.ForeignKey(ProcessingLevel, db_column='processinglevelid')
    result_datetime = models.DateTimeField(db_column='resultdatetime', blank=True, null=True)
    result_datetime_utc_offset = models.BigIntegerField(db_column='resultdatetimeutcoffset', blank=True, null=True)
    valid_datetime = models.DateTimeField(db_column='validdatetime', blank=True, null=True)
    valid_datetime_utc_offset = models.BigIntegerField(db_column='validdatetimeutcoffset', blank=True, null=True)
    status = models.ForeignKey('Status', db_column='statuscv', blank=True)
    sampled_medium = models.ForeignKey('Medium', db_column='sampledmediumcv')
    value_count = models.IntegerField(db_column='valuecount', default=0)

    data_sets = models.ManyToManyField('DataSet', related_name='results', through='DataSetResult')
    data_quality_values = models.ManyToManyField('DataQuality', related_name='results', through='ResultDataQuality')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_results', through='ResultAnnotation')
    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='results',
                                                       through='ResultExtensionPropertyValue')

    objects = ResultManager()

    def __str__(self):
        return '%s - %s (%s): %s %s' % (
            self.result_datetime, self.result_type_id, self.variable.variable_name_id,
            self.variable.variable_code, self.unit.unit_abbreviation
        )

    def __repr__(self):
        return "<Result('%s', '%s', '%s', '%s', '%s')>" % (
            self.result_id, self.result_uuid, self.result_type_id,
            self.processing_level.processing_level_code, self.value_count
        )

    class Meta:
        db_table = 'results'

# endregion

# region ODM2 Equipment Extension


@python_2_unicode_compatible
class DataLoggerProgramFile(models.Model):
    program_id = models.AutoField(db_column='programid', primary_key=True)
    affiliation = models.ForeignKey('Affiliation', db_column='affiliationid', related_name='data_logger_programs')
    program_name = models.CharField(db_column='programname', max_length=255)
    program_description = models.CharField(db_column='programdescription', blank=True, max_length=500)
    program_version = models.CharField(db_column='programversion', blank=True, max_length=50)
    program_file_link = models.FileField(db_column='programfilelink', blank=True)

    def __str__(self):
        return '%s %s' % (self.program_name, self.program_version)

    def __repr__(self):
        return "<DataLoggerProgramFile('%s', '%s', '%s')>" % (
            self.program_id, self.program_name, self.program_version
        )

    class Meta:
        db_table = 'dataloggerprogramfiles'


@python_2_unicode_compatible
class DataLoggerFile(models.Model):
    data_logger_file_id = models.AutoField(db_column='dataloggerfileid', primary_key=True)
    program = models.ForeignKey('DataLoggerProgramFile', db_column='programid', related_name='data_logger_files')
    data_logger_file_name = models.CharField(db_column='dataloggerfilename', max_length=255)
    data_logger_file_description = models.CharField(db_column='dataloggerfiledescription', blank=True, max_length=500)
    data_logger_file_link = models.FileField(db_column='dataloggerfilelink', blank=True)

    objects = DataLoggerFileManager()

    def __str__(self):
        return '%s in %s' % (self.data_logger_file_name, self.program)

    def __repr__(self):
        return "<DataLoggerFile('%s', '%s', '%s', DataLoggerProgramFile[%s, %s])>" % (
            self.data_logger_file_id, self.data_logger_file_name,
            self.data_logger_file_link, self.program_id, self.program
        )

    class Meta:
        db_table = 'dataloggerfiles'


@python_2_unicode_compatible
class DataLoggerFileColumn(models.Model):
    data_logger_file_column_id = models.AutoField(db_column='dataloggerfilecolumnid', primary_key=True)
    result = models.ForeignKey('Result', related_name='data_logger_file_columns', db_column='resultid', blank=True, null=True)
    data_logger_file = models.ForeignKey('DataLoggerFile', related_name='data_logger_file_columns', db_column='dataloggerfileid')
    instrument_output_variable = models.ForeignKey('InstrumentOutputVariable', related_name='data_logger_file_columns', db_column='instrumentoutputvariableid')
    column_label = models.CharField(db_column='columnlabel', max_length=50)
    column_description = models.CharField(db_column='columndescription', blank=True, max_length=500)
    measurement_equation = models.CharField(db_column='measurementequation', blank=True, max_length=255)
    scan_interval = models.FloatField(db_column='scaninterval', blank=True, null=True)
    scan_interval_unit = models.ForeignKey('Unit', related_name='scan_interval_data_logger_file_columns', db_column='scanintervalunitsid', blank=True, null=True)
    recording_interval = models.FloatField(db_column='recordinginterval', blank=True, null=True)
    recording_interval_unit = models.ForeignKey('Unit', related_name='recording_interval_data_logger_file_columns', db_column='recordingintervalunitsid', blank=True, null=True)
    aggregation_statistic = models.ForeignKey('AggregationStatistic', related_name='data_logger_file_columns', db_column='aggregationstatisticcv', blank=True)

    def __str__(self):
        return '%s %s' % (self.column_label, self.column_description)

    def __repr__(self):
        return "<DataLoggerFileColumn('%s', '%s', Result['%s', '%s'])>" % (
            self.data_logger_file_column_id, self.column_label, self.result_id, self.result
        )

    class Meta:
        db_table = 'dataloggerfilecolumns'


@python_2_unicode_compatible
class EquipmentModel(models.Model):
    equipment_model_id = models.AutoField(db_column='equipmentmodelid', primary_key=True)
    model_manufacturer = models.ForeignKey('Organization', db_column='modelmanufacturerid')
    model_part_number = models.CharField(db_column='modelpartnumber', blank=True, max_length=50)
    model_name = models.CharField(db_column='modelname', max_length=255)
    model_description = models.CharField(db_column='modeldescription', blank=True, max_length=500)
    is_instrument = models.BooleanField(db_column='isinstrument', default=None)
    model_specifications_file_link = models.FileField(db_column='modelspecificationsfilelink', blank=True)
    model_link = models.CharField(db_column='modellink', blank=True, max_length=255)

    output_variables = models.ManyToManyField('Variable', related_name='instrument_models', through='InstrumentOutputVariable')
    output_units = models.ManyToManyField('Unit', related_name='instrument_models', through='InstrumentOutputVariable')

    objects = EquipmentModelQuerySet.as_manager()

    def __str__(self):
        return '%s' % self.model_name

    def __repr__(self):
        return "<EquipmentModel('%s', '%s', '%s', Organization[%s, %s])>" % (
            self.equipment_model_id, self.model_name, self.model_description,
            self.model_manufacturer_id, self.model_manufacturer
        )

    class Meta:
        db_table = 'equipmentmodels'
        ordering = ['model_manufacturer', 'model_name']


@python_2_unicode_compatible
class InstrumentOutputVariable(models.Model):
    instrument_output_variable_id = models.AutoField(db_column='instrumentoutputvariableid', primary_key=True)
    model = models.ForeignKey('EquipmentModel', related_name='instrument_output_variables', db_column='modelid')
    variable = models.ForeignKey('Variable', related_name='instrument_output_variables', db_column='variableid')
    instrument_method = models.ForeignKey('Method', related_name='instrument_output_variables', db_column='instrumentmethodid')
    instrument_resolution = models.CharField(db_column='instrumentresolution', blank=True, max_length=255)
    instrument_accuracy = models.CharField(db_column='instrumentaccuracy', blank=True, max_length=255)
    instrument_raw_output_unit = models.ForeignKey('Unit', related_name='instrument_output_variables', db_column='instrumentrawoutputunitsid')

    objects = InstrumentOutputVariableManager()

    def __str__(self):
        return '%s: %s measured in %s' % (
            self.model.model_manufacturer, self.variable.variable_code,
            self.instrument_raw_output_unit.unit_abbreviation
        )

    def __repr__(self):
        return "<InstrumentOutputVariable('%s', EquipmentModel['%s', '%s'], Variable['%s', '%s'], Unit['%s', '%s'], Method['%s', '%s'])>" % (
            self.instrument_output_variable_id, self.model_id, self.model, self.variable_id, self.variable,
            self.instrument_raw_output_unit_id, self.instrument_raw_output_unit,
            self.instrument_method_id, self.instrument_method
        )

    class Meta:
        db_table = 'instrumentoutputvariables'
        ordering = ['model__model_manufacturer', 'variable__variable_code']


@python_2_unicode_compatible
class Equipment(models.Model):
    equipment_id = models.AutoField(db_column='equipmentid', primary_key=True)
    equipment_code = models.CharField(db_column='equipmentcode', max_length=50)
    equipment_name = models.CharField(db_column='equipmentname', max_length=255)
    equipment_type = models.ForeignKey('EquipmentType', db_column='equipmenttypecv')
    equipment_model = models.ForeignKey('EquipmentModel', related_name='equipment', db_column='equipmentmodelid')
    equipment_serial_number = models.CharField(db_column='equipmentserialnumber', max_length=50)
    equipment_owner = models.ForeignKey('People', related_name='owned_equipment', db_column='equipmentownerid')
    equipment_vendor = models.ForeignKey('Organization', related_name='equipment', db_column='equipmentvendorid')
    equipment_purchase_date = models.DateTimeField(db_column='equipmentpurchasedate')
    equipment_purchase_order_number = models.CharField(db_column='equipmentpurchaseordernumber', blank=True, max_length=50)
    equipment_description = models.CharField(db_column='equipmentdescription', blank=True, max_length=500)
    equipment_documentation_link = models.FileField(db_column='equipmentdocumentationlink', blank=True)

    annotations = models.ManyToManyField('Annotation', related_name='annotated_equipment', through='EquipmentAnnotation')
    objects = EquipmentManager()

    def __str__(self):
        return '%s %s (%s)' % (
            self.equipment_serial_number, self.equipment_model, self.equipment_type_id
        )

    def __repr__(self):
        return "<Equipment('%s', '%s', '%s', '%s', '%s', EquipmentModel['%s', '%s'], Person['%s', '%s'], Organization['%s', '%s'])>" % (
            self.equipment_id, self.equipment_code, self.equipment_type,
            self.equipment_serial_number, self.equipment_purchase_date,
            self.equipment_model_id, self.equipment_model,
            self.equipment_owner_id, self.equipment_owner,
            self.equipment_vendor_id, self.equipment_vendor,
        )

    class Meta:
        db_table = 'equipment'


@python_2_unicode_compatible
class CalibrationReferenceEquipment(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    action = models.ForeignKey('CalibrationAction', related_name='+', db_column='actionid')
    equipment = models.ForeignKey('Equipment', related_name='+', db_column='equipmentid')

    objects = CalibrationReferenceEquipmentManager()

    def __str__(self):
        return '%s of %s' % (self.action, self.equipment)

    def __repr__(self):
        return "<CalibrationReferenceEquipment('%s', CalibrationAction['%s', '%s'], Equipment['%s', '%s'])>" % (
            self.bridge_id, self.action_id, self.action, self.equipment_id, self.equipment
        )

    class Meta:
        db_table = 'calibrationreferenceequipment'


@python_2_unicode_compatible
class EquipmentUsed(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    action = models.ForeignKey('Action', related_name='+', db_column='actionid')
    equipment = models.ForeignKey('Equipment', related_name='+', db_column='equipmentid')

    objects = EquipmentUsedManager()

    def __str__(self):
        return '%s of %s' % (self.action, self.equipment)

    def __repr__(self):
        return "<EquipmentUsed('%s', Action['%s', '%s'], Equipment['%s', '%s'])>" % (
            self.bridge_id, self.action_id, self.action, self.equipment_id, self.equipment
        )

    class Meta:
        db_table = 'equipmentused'


@python_2_unicode_compatible
class MaintenanceAction(models.Model):
    action = models.OneToOneField(Action, related_name='maintenance', db_column='actionid', primary_key=True)
    is_factory_service = models.BooleanField(db_column='isfactoryservice', default=None)
    maintenance_code = models.CharField(db_column='maintenancecode', blank=True, max_length=50)
    maintenance_reason = models.CharField(db_column='maintenancereason', blank=True, max_length=500)

    objects = MaintenanceActionManager()

    def __str__(self):
        return '%s: %s - %s' % (self.action, self.maintenance_code, self.maintenance_reason)

    def __repr__(self):
        return "<MaintenanceAction('%s', '%s', '%s', '%s')>" % (
            self.action_id, self.action.begin_datetime, self.maintenance_code, self.maintenance_reason
        )

    class Meta:
        db_table = 'maintenanceactions'


class RelatedEquipment(ObjectRelation):
    equipment = models.ForeignKey('Equipment', related_name='related_equipment', db_column='equipmentid')
    related_equipment = models.ForeignKey('Equipment', related_name='reverse_related_equipment', db_column='relatedequipmentid')
    relationship_start_datetime = models.DateTimeField(db_column='relationshipstartdatetime')
    relationship_start_datetime_utc_offset = models.IntegerField(db_column='relationshipstartdatetimeutcoffset')
    relationship_end_datetime = models.DateTimeField(db_column='relationshipenddatetime', blank=True, null=True)
    relationship_end_datetime_utc_offset = models.IntegerField(db_column='relationshipenddatetimeutcoffset', blank=True, null=True)

    objects = RelatedEquipmentManager()

    def __str__(self):
        return '%s %s %s' % (self.equipment, self.relationship_type_id, self.related_equipment)

    def __repr__(self):
        return "<RelatedEquipment('%s', Equipment['%s', '%s'], '%s', Equipment['%s', '%s'])>" % (
            self.relation_id, self.equipment_id, self.equipment, self.relationship_type_id,
            self.related_equipment_id, self.related_equipment
        )

    class Meta:
        db_table = 'relatedequipment'


@python_2_unicode_compatible
class CalibrationAction(models.Model):
    action = models.OneToOneField(Action, related_name='calibration', db_column='actionid', primary_key=True)
    calibration_check_value = models.FloatField(db_column='calibrationcheckvalue', blank=True, null=True)
    instrument_output_variable = models.ForeignKey('InstrumentOutputVariable', db_column='instrumentoutputvariableid')
    calibration_equation = models.CharField(db_column='calibrationequation', blank=True, max_length=255)

    calibration_standards = models.ManyToManyField('ReferenceMaterial', related_name='calibration_actions', through='CalibrationStandard')
    reference_equipment = models.ManyToManyField('Equipment', related_name='calibration_reference_actions', through='CalibrationReferenceEquipment')
    objects = CalibrationActionManager()

    def __str__(self):
        return '%s: %s' % (self.action, self.instrument_output_variable)

    def __repr__(self):
        return "<CalibrationAction('%s', '%s', '%s', '%s', InstrumentOutputVariable['%s', '%s'])>" % (
            self.action_id, self.action.begin_datetime, self.calibration_equation, self.calibration_check_value,
            self.instrument_output_variable_id, self.instrument_output_variable
        )

    class Meta:
        db_table = 'calibrationactions'

# endregion

# region ODM2 Lab Analyses Extension


class Directive(models.Model):
    directive_id = models.AutoField(db_column='directiveid', primary_key=True)
    directive_type = models.ForeignKey('DirectiveType', db_column='directivetypecv')
    directive_description = models.CharField(db_column='directivedescription', max_length=500)

    def __repr__(self):
        return "<Directive('%s', '%s', '%s')>" % (
            self.directive_id, self.directive_type_id, self.directive_description
        )

    class Meta:
        db_table = 'directives'


class ActionDirective(models.Model):
    bridge_id = models.IntegerField(db_column='bridgeid', primary_key=True)
    action = models.ForeignKey('Action', related_name='+', db_column='actionid')
    directive = models.ForeignKey('Directive', related_name='+', db_column='directiveid')

    def __repr__(self):
        return "<ActionDirective('%s', Action['%s', '%s'], Directive['%s', '%s'])>" % (
            self.bridge_id, self.action_id, self.action, self.directive_id, self.directive
        )

    class Meta:
        db_table = 'actiondirectives'


class SpecimenBatchPosition(models.Model):
    feature_action = models.OneToOneField('FeatureAction', db_column='featureactionid', primary_key=True)
    batch_position_number = models.IntegerField(db_column='batchpositionnumber')
    batch_position_label = models.CharField(db_column='batchpositionlabel', blank=True, max_length=255)

    def __repr__(self):
        return "<SpecimenBatchPosition('%s', '%s', '%s')>" % (
            self.feature_action_id, self.batch_position_label, self.batch_position_number
        )

    class Meta:
        db_table = 'specimenbatchpostions'

# endregion

# region ODM2 Sampling Features Extension


class SpatialReference(models.Model):
    spatial_reference_id = models.AutoField(db_column='spatialreferenceid', primary_key=True)
    srs_code = models.CharField(db_column='srscode', blank=True, max_length=50)
    srs_name = models.CharField(db_column='srsname', max_length=255)
    srs_description = models.CharField(db_column='srsdescription', blank=True, max_length=500)
    srs_link = models.CharField(db_column='srslink', blank=True, max_length=255)

    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='spatial_references',
                                                  through='SpatialReferenceExternalIdentifier')

    def __repr__(self):
        return "<SpatialReference('%s', '%s', '%s')>" % (
            self.spatial_reference_id, self.srs_code, self.srs_name
        )

    class Meta:
        db_table = 'spatialreferences'


class Specimen(models.Model):
    sampling_feature = models.OneToOneField('SamplingFeature', db_column='samplingfeatureid', primary_key=True)
    specimen_type = models.ForeignKey('SpecimenType', db_column='specimentypecv')
    specimen_medium = models.ForeignKey('Medium', db_column='specimenmediumcv')
    is_field_specimen = models.BooleanField(db_column='isfieldspecimen', default=None)

    def __repr__(self):
        return "<SpatialReference('%s', '%s', '%s')>" % (
            self.spatial_reference_id, self.srs_code, self.srs_name
        )

    class Meta:
        managed = False
        db_table = 'specimens'


class SpatialOffset(models.Model):
    spatial_offset_id = models.AutoField(db_column='spatialoffsetid', primary_key=True)
    spatial_offset_type = models.ForeignKey('SpatialOffsetType', db_column='spatialoffsettypecv')
    offset_1_value = models.FloatField(db_column='offset1value')
    offset_1_unit = models.ForeignKey('Unit', related_name='+', db_column='offset1unitid')
    offset_2_value = models.FloatField(db_column='offset2value', blank=True, null=True)
    offset_2_unit = models.ForeignKey('Unit', related_name='+', db_column='offset2unitid', blank=True, null=True)
    offset_3_value = models.FloatField(db_column='offset3value', blank=True, null=True)
    offset_3_unit = models.ForeignKey('Unit', related_name='+', db_column='offset3unitid', blank=True, null=True)

    def __repr__(self):
        return "<SpatialOffset('%s', '%s', '%s')>" % (
            self.spatial_offset_id, self.spatial_offset_type_id, self.srs_name
        )

    class Meta:
        db_table = 'spatialoffsets'


class Site(models.Model):
    sampling_feature = models.OneToOneField('SamplingFeature', related_name='site', db_column='samplingfeatureid', primary_key=True)
    site_type = models.ForeignKey('SiteType', db_column='sitetypecv')
    latitude = models.FloatField(db_column='latitude')
    longitude = models.FloatField(db_column='longitude')
    spatial_reference = models.ForeignKey('SpatialReference', db_column='spatialreferenceid')

    def __repr__(self):
        return "<Site('%s', '%s', '%s', '%s')>" % (
            self.sampling_feature_id, self.site_type_id, self.latitude, self.longitude
        )

    class Meta:
        db_table = 'sites'


class RelatedFeature(ObjectRelation):
    sampling_feature = models.ForeignKey('SamplingFeature', related_name='related_features_sampling_feature', db_column='samplingfeatureid')
    related_feature = models.ForeignKey('SamplingFeature', related_name='related_features_related_feature', db_column='relatedfeatureid')
    spatial_offset = models.ForeignKey('SpatialOffset', db_column='spatialoffsetid', blank=True, null=True)

    def __repr__(self):
        return "<RelatedFeature('%s', SamplingFeature['%s', '%s'], '%s', SamplingFeature['%s', '%s'])>" % (
            self.relation_id, self.sampling_feature_id, self.sampling_feature,
            self.relationship_type_id, self.related_feature_id, self.related_feature
        )

    class Meta:
        db_table = 'relatedfeatures'


class SpecimenTaxonomicClassifier(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    sampling_feature = models.ForeignKey('Specimen', related_name='taxonomic_classifiers', db_column='samplingfeatureid')
    taxonomic_classifier = models.ForeignKey('TaxonomicClassifier', related_name='specimens', db_column='taxonomicclassifierid')
    citation = models.ForeignKey('Citation', related_name='specimen_taxonomic_classifiers', db_column='citationid', blank=True, null=True)

    def __repr__(self):
        return "<SpecimenTaxonomicClassifier('%s', SamplingFeature['%s', '%s'], TaxonomicClassifier['%s', '%s'])>" % (
            self.bridge_id, self.sampling_feature_id, self.sampling_feature,
            self.taxonomic_classifier_id, self.taxonomic_classifier
        )

    class Meta:
        db_table = 'specimentaxonomicclassifiers'

# endregion

# region ODM2 Simulation Extension


class Model(models.Model):
    model_id = models.AutoField(db_column='modelid', primary_key=True)
    model_code = models.CharField(db_column='modelcode', max_length=255)
    model_name = models.CharField(db_column='modelname', max_length=255)
    model_description = models.CharField(db_column='modeldescription', max_length=500, blank=True)
    version = models.CharField(db_column='version', blank=True, max_length=255)
    model_link = models.CharField(db_column='modellink', blank=True, max_length=255)

    def __repr__(self):
        return "<Model('%s', '%s', '%s', '%s')>" % (
            self.model_id, self.model_code, self.model_name, self.version
        )

    class Meta:
        db_table = 'models'


class RelatedModel(ObjectRelation):
    model = models.ForeignKey('Model', related_name='related_model_model', db_column='modelid')
    related_model = models.ForeignKey('Model', related_name='related_model_related_model', db_column='relatedmodelid')

    def __repr__(self):
        return "<RelatedModel('%s', Model['%s', '%s'], Model['%s', '%s'])>" % (
            self.relation_id, self.model_id, self.model, self.related_model_id, self.related_model
        )

    class Meta:
        db_table = 'relatedmodels'


class Simulation(models.Model):
    simulation_id = models.AutoField(db_column='simulationid', primary_key=True)
    action = models.ForeignKey('Action', related_name='simulations', db_column='actionid')
    simulation_name = models.CharField(db_column='simulationname', max_length=255)
    simulation_description = models.CharField(db_column='simulationdescription', max_length=500, blank=True)
    simulation_start_datetime = models.DateTimeField(db_column='simulationstartdatetime')
    simulation_start_datetime_utc_offset = models.IntegerField(db_column='simulationstartdatetimeutcoffset')
    simulation_end_datetime = models.DateTimeField(db_column='simulationenddatetime')
    simulation_end_datetime_utc_offset = models.IntegerField(db_column='simulationenddatetimeutcoffset')
    time_step_value = models.FloatField(db_column='timestepvalue')
    time_step_unit = models.ForeignKey('Unit', related_name='simulations', db_column='timestepunitsid')
    input_data_set = models.ForeignKey('DataSet', related_name='simulations', db_column='inputdatasetid', blank=True, null=True)
    model = models.ForeignKey('Model', related_name='simulations', db_column='modelid')

    def __repr__(self):
        return "<Simulation('%s', '%s', '%s', '%s')>" % (
            self.simulation_id, self.simulation_name, self.simulation_start_datetime, self.simulation_end_datetime
        )

    class Meta:
        db_table = 'simulations'


class Citation(models.Model):
    citation_id = models.AutoField(db_column='citationid', primary_key=True)
    title = models.CharField(db_column='title', max_length=255)
    publisher = models.CharField(db_column='publisher', max_length=255)
    publication_year = models.IntegerField(db_column='publicationyear')
    citation_link = models.CharField(db_column='citationlink', blank=True, max_length=255)

    extension_property_values = models.ManyToManyField('ExtensionProperty', related_name='citations',
                                                       through='CitationExtensionPropertyValue')
    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='citations',
                                                  through='CitationExternalIdentifier')

    def __repr__(self):
        return "<Citation('%s', '%s', '%s', '%s')>" % (
            self.citation_id, self.title, self.publisher, self.publication_year
        )

    class Meta:
        db_table = 'citations'

# endregion

# region Annotations


class Annotation(models.Model):
    annotation_id = models.AutoField(db_column='annotationid', primary_key=True)
    annotation_type = models.ForeignKey('AnnotationType', db_column='annotationtypecv')
    annotation_code = models.CharField(db_column='annotationcode', blank=True, max_length=50)
    annotation_text = models.CharField(db_column='annotationtext', max_length=500)
    annotation_datetime = models.DateTimeField(db_column='annotationdatetime', blank=True, null=True)
    annotation_utc_offset = models.IntegerField(db_column='annotationutcoffset', blank=True, null=True)
    annotation_link = models.CharField(db_column='annotationlink', blank=True, max_length=255)
    annotator = models.ForeignKey('People', db_column='annotatorid', blank=True, null=True)
    citation = models.ForeignKey('Citation', db_column='citationid', blank=True, null=True)

    def __repr__(self):
        return "<Annotation('%s', '%s', '%s', '%s', '%s')>" % (
            self.annotation_id, self.annotation_type_id, self.annotation_datetime,
            self.annotation_code, self.annotation_text
        )

    class Meta:
        db_table = 'annotations'


class ActionAnnotation(AnnotationBridge):
    action = models.ForeignKey('Action', related_name='+', db_column='actionid')

    def __repr__(self):
        return "<ActionAnnotation('%s', Annotation['%s', '%s'], Action['%s', '%s'])>" % (
            self.bridge_id, self.annotation_id, self.annotation, self.action_id, self.action
        )

    class Meta:
        db_table = 'actionannotations'


class EquipmentAnnotation(AnnotationBridge):
    equipment = models.ForeignKey('Equipment', related_name='+', db_column='equipmentid')

    def __repr__(self):
        return "<EquipmentAnnotation('%s', Annotation['%s', '%s'], Equipment['%s', '%s'])>" % (
            self.bridge_id, self.annotation_id, self.annotation, self.equipment_id, self.equipment
        )

    class Meta:
        db_table = 'equipmentannotations'


class MethodAnnotation(AnnotationBridge):
    method = models.ForeignKey('Method', related_name='+', db_column='methodid')

    def __repr__(self):
        return "<MethodAnnotation('%s', Annotation['%s', '%s'], Method['%s', '%s'])>" % (
            self.bridge_id, self.annotation_id, self.annotation, self.method_id, self.method
        )

    class Meta:
        db_table = 'methodannotations'


class ResultAnnotation(AnnotationBridge):
    result = models.ForeignKey('Result', related_name='dated_annotations', db_column='resultid')
    begin_datetime = models.DateTimeField(db_column='begindatetime')
    end_datetime = models.DateTimeField(db_column='enddatetime')

    def __repr__(self):
        return "<ResultAnnotation('%s', Annotation['%s', '%s'], Result['%s', '%s'])>" % (
            self.bridge_id, self.annotation_id, self.annotation, self.result_id, self.result
        )

    class Meta:
        db_table = 'resultannotations'


class SamplingFeatureAnnotation(AnnotationBridge):
    sampling_feature = models.ForeignKey('SamplingFeature', related_name='+', db_column='samplingfeatureid')

    def __repr__(self):
        return "<SamplingFeatureAnnotation('%s', Annotation['%s', '%s'], SamplingFeature['%s', '%s'])>" % (
            self.bridge_id, self.annotation_id, self.annotation, self.sampling_feature_id, self.sampling_feature
        )

    class Meta:
        db_table = 'samplingfeatureannotations'

# endregion

# region Data Quality


class DataSetResult(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    data_set = models.ForeignKey('DataSet', related_name='+', db_column='datasetid')
    result = models.ForeignKey('Result', related_name='+', db_column='resultid')

    def __repr__(self):
        return "<DataSetResult('%s', Result['%s', '%s'], DataSet['%s', '%s'])>" % (
            self.bridge_id, self.result_id, self.result, self.data_set_id, self.data_set
        )

    class Meta:
        db_table = 'datasetsresults'


class DataQuality(models.Model):
    data_quality_id = models.AutoField(db_column='dataqualityid', primary_key=True)
    data_quality_type = models.ForeignKey('DataQualityType', db_column='dataqualitytypecv')
    data_quality_code = models.CharField(db_column='dataqualitycode', max_length=255)
    data_quality_value = models.FloatField(db_column='dataqualityvalue', blank=True, null=True)
    data_quality_value_unit = models.ForeignKey('Unit', db_column='dataqualityvalueunitsid', blank=True, null=True)
    data_quality_description = models.CharField(db_column='dataqualitydescription', blank=True, max_length=500)
    data_quality_link = models.CharField(db_column='dataqualitylink', blank=True, max_length=255)

    def __repr__(self):
        return "<DataQuality('%s', '%s', '%s', '%s')>" % (
            self.data_quality_id, self.data_quality_type_id, self.data_quality_code, self.data_quality_value
        )

    class Meta:
        db_table = 'dataquality'


class ReferenceMaterial(models.Model):
    reference_material_id = models.AutoField(db_column='referencematerialid', primary_key=True)
    reference_material_medium = models.ForeignKey('Medium', db_column='referencematerialmediumcv')
    reference_material_organization = models.ForeignKey('Organization', db_column='referencematerialorganizationid')
    reference_material_code = models.CharField(db_column='referencematerialcode', max_length=50)
    reference_material_lot_code = models.CharField(db_column='referencemateriallotcode', blank=True, max_length=255)
    reference_material_purchase_date = models.DateTimeField(db_column='referencematerialpurchasedate', blank=True, null=True)
    reference_material_expiration_date = models.DateTimeField(db_column='referencematerialexpirationdate', blank=True, null=True)
    reference_material_certificate_link = models.FileField(db_column='referencematerialcertificatelink', blank=True)  # TODO: is it a link or a file link?  BOTH
    sampling_feature = models.ForeignKey('SamplingFeature', db_column='samplingfeatureid', blank=True, null=True)

    external_identifiers = models.ManyToManyField('ExternalIdentifierSystem', related_name='reference_materials',
                                                  through='ReferenceMaterialExternalIdentifier')

    def __repr__(self):
        return "<ReferenceMaterial('%s', '%s', '%s', Organization['%s', '%s'])>" % (
            self.reference_material_id, self.reference_material_code, self.reference_material_purchase_date,
            self.reference_material_organization_id, self.reference_material_organization
        )

    class Meta:
        db_table = 'referencematerials'


class CalibrationStandard(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    action = models.ForeignKey('CalibrationAction', related_name='+', db_column='actionid')
    reference_material = models.ForeignKey('ReferenceMaterial', related_name='+', db_column='calibration_standards')

    def __repr__(self):
        return "<CalibrationStandard('%s', CalibrationAction['%s', '%s'], ReferenceMaterial['%s', '%s'])>" % (
            self.bridge_id, self.action_id, self.action, self.reference_material_id, self.reference_material
        )

    class Meta:
        db_table = 'calibrationstandards'


class ReferenceMaterialValue(models.Model):
    reference_material_value_id = models.AutoField(db_column='referencematerialvalueid', primary_key=True)
    reference_material = models.ForeignKey('ReferenceMaterial', related_name='referencematerialvalue', db_column='referencematerialid')
    reference_material_value = models.FloatField(db_column='referencematerialvalue')
    reference_material_accuracy = models.FloatField(db_column='referencematerialaccuracy', blank=True, null=True)
    variable = models.ForeignKey('Variable', db_column='variableid')
    unit = models.ForeignKey('Unit', db_column='unitsid')
    citation = models.ForeignKey('Citation', db_column='citationid', blank=True, null=True)

    def __repr__(self):
        return "<ReferenceMaterialValue('%s', ReferenceMaterial['%s', '%s'], '%s')>" % (
            self.reference_material_value_id, self.reference_material_id, self.reference_material, self.reference_material_value
        )

    class Meta:
        db_table = 'referencematerialvalues'


class ResultNormalizationValue(models.Model):
    result = models.OneToOneField('Result', db_column='resultid', primary_key=True)
    normalized_by_reference_material_value = models.ForeignKey('ReferenceMaterialValue', db_column='normalizedbyreferencematerialvalueid')

    def __repr__(self):
        return "<ResultNormalizationValue('%s', '%s', ReferenceMaterialValue['%s', '%s'])>" % (
            self.result_id, self.result, self.normalized_by_reference_material_value_id,
            self.normalized_by_reference_material_value
        )

    class Meta:
        db_table = 'resultnormalizationvalues'


class ResultDataQuality(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    result = models.ForeignKey('Result', related_name='+', db_column='resultid')
    data_quality = models.ForeignKey('DataQuality', related_name='+', db_column='dataqualityid')

    def __repr__(self):
        return "<ResultDataQuality('%s', Result['%s', '%s'], DataQuality['%s', '%s'])>" % (
            self.bridge_id, self.result_id, self.result, self.data_quality_id, self.data_quality
        )

    class Meta:
        db_table = 'resultsdataquality'

# endregion

# region Extension Properties


class ExtensionProperty(models.Model):
    property_id = models.AutoField(db_column='propertyid', primary_key=True)
    property_name = models.CharField(db_column='propertyname', max_length=255)
    property_description = models.CharField(db_column='propertydescription', blank=True, max_length=500)
    property_data_type = models.ForeignKey('PropertyDataType', db_column='propertydatatypecv')
    property_units = models.ForeignKey('Unit', db_column='propertyunitsid', blank=True, null=True)

    def __repr__(self):
        return "<ExtensionProperty('%s', '%s', '%s')>" % (
            self.property_id, self.property_name, self.property_data_type_id
        )

    class Meta:
        db_table = 'extensionproperties'


class ActionExtensionPropertyValue(ExtensionPropertyBridge):
    action = models.ForeignKey('Action', db_column='actionid')

    def __repr__(self):
        return "<ActionExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], Action['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property, self.action_id, self.action
        )

    class Meta:
        db_table = 'actionextensionpropertyvalues'


class CitationExtensionPropertyValue(ExtensionPropertyBridge):
    citation = models.ForeignKey('Citation', db_column='citationid')

    def __repr__(self):
        return "<CitationExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], Citation['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.citation_id, self.citation
        )

    class Meta:
        db_table = 'citationextensionpropertyvalues'


class MethodExtensionPropertyValue(ExtensionPropertyBridge):
    method = models.ForeignKey('Method', db_column='methodid')

    def __repr__(self):
        return "<MethodExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], Method['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.method_id, self.method
        )

    class Meta:
        db_table = 'methodextensionpropertyvalues'


class ResultExtensionPropertyValue(ExtensionPropertyBridge):
    result = models.ForeignKey('Result', db_column='resultid')

    def __repr__(self):
        return "<ResultExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], Result['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.result_id, self.result
        )

    class Meta:
        db_table = 'resultextensionpropertyvalues'


class SamplingFeatureExtensionPropertyValue(ExtensionPropertyBridge):
    sampling_feature = models.ForeignKey('SamplingFeature', db_column='samplingfeatureid')

    def __repr__(self):
        return "<SamplingFeatureExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], SamplingFeature['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.sampling_feature_id, self.sampling_feature
        )

    class Meta:
        db_table = 'samplingfeatureextensionpropertyvalues'


class VariableExtensionPropertyValue(ExtensionPropertyBridge):
    variable = models.ForeignKey('Variable', db_column='variableid')

    def __repr__(self):
        return "<VariableExtensionPropertyValue('%s', '%s', ExtensionProperty['%s', '%s'], Variable['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.variable_id, self.variable
        )

    class Meta:
        db_table = 'variableextensionpropertyvalues'

# endregion

# region Extension Identifiers


class ExternalIdentifierSystem(models.Model):
    external_identifier_system_id = models.AutoField(db_column='externalidentifiersystemid', primary_key=True)
    external_identifier_system_name = models.CharField(db_column='externalidentifiersystemname', max_length=255)
    identifier_system_organization = models.ForeignKey('Organization', db_column='identifiersystemorganizationid')
    external_identifier_system_description = models.CharField(db_column='externalidentifiersystemdescription', blank=True, max_length=500)
    external_identifier_system_url = models.CharField(db_column='externalidentifiersystemurl', blank=True, max_length=255)

    def __repr__(self):
        return "<ExternalIdentifierSystem('%s', '%s', Organization['%s', '%s'])>" % (
            self.external_identifier_system_id, self.external_identifier_system_name,
            self.identifier_system_organization_id, self.identifier_system_organization
        )

    class Meta:
        db_table = 'externalidentifiersystems'


class CitationExternalIdentifier(ExternalIdentifierBridge):
    citation = models.ForeignKey('Citation', db_column='citationid')
    citation_external_identifier = models.CharField(db_column='citationexternalidentifier', max_length=255)
    citation_external_identifier_uri = models.CharField(db_column='citationexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<CitationExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], Citation['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property, self.citation_id, self.citation
        )

    class Meta:
        db_table = 'citationexternalidentifiers'


class MethodExternalIdentifier(ExternalIdentifierBridge):
    method = models.ForeignKey('Method', db_column='methodid')
    method_external_identifier = models.CharField(db_column='methodexternalidentifier', max_length=255)
    method_external_identifier_uri = models.CharField(db_column='methodexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<MethodExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], Method['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property, self.method_id, self.method
        )

    class Meta:
        db_table = 'methodexternalidentifiers'


class PersonExternalIdentifier(ExternalIdentifierBridge):
    person = models.ForeignKey('People', db_column='personid')
    person_external_identifier = models.CharField(db_column='personexternalidentifier', max_length=255)
    person_external_identifier_uri = models.CharField(db_column='personexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<PersonExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], Person['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.person_id, self.person
        )

    class Meta:
        db_table = 'personexternalidentifiers'


class ReferenceMaterialExternalIdentifier(ExternalIdentifierBridge):
    reference_material = models.ForeignKey('ReferenceMaterial', db_column='referencematerialid')
    reference_material_external_identifier = models.CharField(db_column='referencematerialexternalidentifier', max_length=255)
    reference_material_external_identifier_uri = models.CharField(db_column='referencematerialexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<ReferenceMaterialExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], ReferenceMaterial['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.reference_material_id, self.reference_material
        )

    class Meta:
        db_table = 'referencematerialexternalidentifiers'


class SamplingFeatureExternalIdentifier(ExternalIdentifierBridge):
    sampling_feature = models.ForeignKey('SamplingFeature', db_column='samplingfeatureid')
    sampling_feature_external_identifier = models.CharField(db_column='samplingfeatureexternalidentifier', max_length=255)
    sampling_feature_external_identifier_uri = models.CharField(db_column='samplingfeatureexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<SamplingFeatureExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], SamplingFeature['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.sampling_feature_id, self.sampling_feature
        )

    class Meta:
        db_table = 'samplingfeatureexternalidentifiers'


class SpatialReferenceExternalIdentifier(ExternalIdentifierBridge):
    spatial_reference = models.ForeignKey('SpatialReference', db_column='spatialreferenceid')
    spatial_reference_external_identifier = models.CharField(db_column='spatialreferenceexternalidentifier', max_length=255)
    spatial_reference_external_identifier_uri = models.CharField(db_column='spatialreferenceexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<SpatialReferenceExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], SpatialReference['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.spatial_reference_id, self.spatial_reference
        )

    class Meta:
        db_table = 'spatialreferenceexternalidentifiers'


class TaxonomicClassifierExternalIdentifier(ExternalIdentifierBridge):
    taxonomic_classifier = models.ForeignKey('TaxonomicClassifier', db_column='taxonomicclassifierid')
    taxonomic_classifier_external_identifier = models.CharField(db_column='taxonomicclassifierexternalidentifier', max_length=255)
    taxonomic_classifier_external_identifier_uri = models.CharField(db_column='taxonomicclassifierexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<TaxonomicClassifierExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], TaxonomicClassifier['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property,
            self.taxonomic_classifier_id, self.taxonomic_classifier
        )

    class Meta:
        db_table = 'taxonomicclassifierexternalidentifiers'


class VariableExternalIdentifier(ExternalIdentifierBridge):
    variable = models.ForeignKey('Variable', db_column='variableid')
    variable_external_identifier = models.CharField(db_column='variableexternalidentifer', max_length=255)
    variable_external_identifier_uri = models.CharField(db_column='variableexternalidentifieruri', blank=True, max_length=255)

    def __repr__(self):
        return "<VariableExternalIdentifier('%s', '%s', ExternalIdentifierSystem['%s', '%s'], Variable['%s', '%s'])>" % (
            self.bridge_id, self.property_value, self.property_id, self.property, self.variable_id, self.variable
        )

    class Meta:
        db_table = 'variableexternalidentifiers'

# endregion

# region Provenance


class AuthorList(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    citation = models.ForeignKey('Citation', db_column='citationid')
    person = models.ForeignKey('People', db_column='personid')
    author_order = models.IntegerField(db_column='authororder')

    def __repr__(self):
        return "<VariableExternalIdentifier('%s', Person['%s', '%s'], Citation['%s', '%s'], '%s')>" % (
            self.bridge_id, self.person_id, self.person, self.citation_id, self.citation, self.author_order
        )

    class Meta:
        db_table = 'authorlists'


class DataSetCitation(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    data_set = models.ForeignKey('DataSet', db_column='datasetid')
    relationship_type = models.ForeignKey('RelationshipType', db_column='relationshiptypecv')
    citation = models.ForeignKey('Citation', db_column='citationid')

    def __repr__(self):
        return "<DataSetCitation('%s', DataSet['%s', '%s'], '%s', Citation['%s', '%s'])>" % (
            self.bridge_id, self.data_set_id, self.data_set, self.relationship_type_id, self.citation_id, self.citation
        )

    class Meta:
        db_table = 'datasetcitations'


class DerivationEquation(models.Model):
    derivation_equation_id = models.AutoField(db_column='derivationequationid', primary_key=True)
    derivation_equation = models.CharField(db_column='derivationequation', max_length=255)

    def __repr__(self):
        return "<DerivationEquation('%s', '%s')>" % (
            self.derivation_equation_id, self.derivation_equation
        )

    class Meta:
        db_table = 'derivationequations'


class ResultDerivationEquation(models.Model):
    result = models.OneToOneField('Result', db_column='resultid', primary_key=True)
    derivation_equation = models.ForeignKey('DerivationEquation', db_column='derivationequationid')

    def __repr__(self):
        return "<ResultDerivationEquation('%s', '%s', DerivationEquation['%s', '%s'])>" % (
            self.result_id, self.result, self.derivation_equation_id, self.derivation_equation
        )

    class Meta:
        db_table = 'resultderivationequations'


class MethodCitation(models.Model):
    bridge_id = models.AutoField(db_column='bridgeid', primary_key=True)
    method = models.ForeignKey('Method', db_column='methodid')
    relationship_type = models.ForeignKey('RelationshipType', db_column='relationshiptypecv')
    citation = models.ForeignKey('Citation', db_column='citationid')

    def __repr__(self):
        return "<MethodCitation('%s', Method['%s', '%s'], '%s', Citation['%s', '%s'])>" % (
            self.bridge_id, self.method_id, self.method, self.relationship_type_id, self.citation_id, self.citation
        )

    class Meta:
        db_table = 'methodcitations'


class RelatedAnnotation(ObjectRelation):
    annotation = models.ForeignKey('Annotation', related_name='related_annonation_annotation', db_column='annotationid')
    related_annotation = models.ForeignKey('Annotation', related_name='related_annotation_related_annontation', db_column='relatedannotationid')

    def __repr__(self):
        return "<RelatedAnnotation('%s', Annotation['%s', '%s'], '%s', Annotation['%s', '%s'])>" % (
            self.relation_id, self.annotation_id, self.annotation, self.relationship_type_id,
            self.related_annotation_id, self.related_annotation
        )

    class Meta:
        db_table = 'relatedannotations'


class RelatedDataSet(ObjectRelation):
    data_set = models.ForeignKey('DataSet', related_name='related_dataset_dataset', db_column='datasetid')
    related_data_set = models.ForeignKey('DataSet', related_name='related_dataset_related_dataset', db_column='relateddatasetid')
    version_code = models.CharField(db_column='versioncode', blank=True, max_length=50)

    def __repr__(self):
        return "<RelatedDataSet('%s', DataSet['%s', '%s'], '%s', DataSet['%s', '%s'], '%s')>" % (
            self.relation_id, self.data_set_id, self.data_set, self.relationship_type_id,
            self.related_data_set_id, self.related_data_set, self.version_code
        )

    class Meta:
        db_table = 'relateddatasets'


class RelatedResult(ObjectRelation):
    result = models.ForeignKey('Result', db_column='resultid')
    related_result = models.ForeignKey('Result', related_name='related_result_related_result', db_column='relatedresultid')
    version_code = models.CharField(db_column='versioncode', blank=True, max_length=50)
    related_result_sequence_number = models.IntegerField(db_column='relatedresultsequencenumber', blank=True, null=True)

    def __repr__(self):
        return "<RelatedResult('%s', Result['%s', '%s'], '%s', Result['%s', '%s'], '%s')>" % (
            self.relation_id, self.result_id, self.result, self.relationship_type_id,
            self.related_result_id, self.related_result, self.version_code
        )

    class Meta:
        db_table = 'relatedresults'

# endregion

# region Results


class PointCoverageResult(ExtendedResult, AggregatedComponent, ZOffsetComponent, XIntendedComponent, YIntendedComponent, TimeAggregationComponent):
    class Meta:
        db_table = 'pointcoverageresults'


class ProfileResult(ExtendedResult, AggregatedComponent, XOffsetComponent, YOffsetComponent, ZIntendedComponent, TimeIntendedComponent):
    class Meta:
        db_table = 'profileresults'


class CategoricalResult(ExtendedResult, XOffsetComponent, YOffsetComponent, ZOffsetComponent):
    quality_code = models.ForeignKey('QualityCode', db_column='qualitycodecv')

    class Meta:
        db_table = 'categoricalresults'


class TransectResult(ExtendedResult, AggregatedComponent, ZOffsetComponent, TimeIntendedComponent):
    intended_transect_spacing = models.FloatField(db_column='intendedtransectspacing')
    intended_transect_spacing_unit = models.ForeignKey('Unit', db_column='intendedtransectspacingunitsid', blank=True, null=True)

    class Meta:
        db_table = 'transectresults'


class SpectraResult(ExtendedResult, AggregatedComponent, XOffsetComponent, YOffsetComponent, ZOffsetComponent):
    intended_wavelength_spacing = models.FloatField(db_column='intendedwavelengthspacing')
    intended_wavelength_spacing_unit = models.ForeignKey('Unit', db_column='intendedwavelengthspacingunitsid', blank=True, null=True)

    class Meta:
        db_table = 'spectraresults'


class TimeSeriesResult(ExtendedResult, AggregatedComponent, XOffsetComponent, YOffsetComponent, ZOffsetComponent, TimeIntendedComponent):
    class Meta:
        db_table = 'timeseriesresults'


class SectionResult(ExtendedResult, AggregatedComponent, YOffsetComponent, XIntendedComponent, ZIntendedComponent, TimeIntendedComponent):
    class Meta:
        db_table = 'sectionresults'


class TrajectoryResult(ExtendedResult, AggregatedComponent, TimeIntendedComponent):
    intended_trajectory_spacing = models.FloatField(db_column='intendedtrajectoryspacing')
    intended_trajectory_spacing_unit = models.ForeignKey('Unit', db_column='intendedtrajectoryspacingunitsid', blank=True, null=True)

    class Meta:
        db_table = 'trajectoryresults'


class MeasurementResult(ExtendedResult, AggregatedComponent, XOffsetComponent, YOffsetComponent, ZOffsetComponent, TimeAggregationComponent, QualityControlComponent):
    class Meta:
        db_table = 'measurementresults'


class CategoricalResultValue(ResultValue):
    result = models.ForeignKey('CategoricalResult', db_column='resultid')
    data_value = models.CharField(db_column='datavalue', max_length=255)
    annotations = models.ManyToManyField('Annotation', related_name='annotated_categorical_values',
                                         through='CategoricalResultValueAnnotation')

    class Meta:
        db_table = 'categoricalresultvalues'


class MeasurementResultValue(ResultValue):
    result = models.ForeignKey('MeasurementResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_measurement_values',
                                         through='MeasurementResultValueAnnotation')

    class Meta:
        db_table = 'measurementresultvalues'


class PointCoverageResultValue(ResultValue, XOffsetComponent, YOffsetComponent, QualityControlComponent):
    result = models.ForeignKey('PointCoverageResult', db_column='resultid')
    data_value = models.BigIntegerField(db_column='datavalue')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_point_coverage_values',
                                         through='PointCoverageResultValueAnnotation')

    class Meta:
        db_table = 'pointcoverageresultvalues'


class ProfileResultValue(ResultValue, ZOffsetComponent, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('ProfileResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    z_aggregation_interval = models.FloatField(db_column='zaggregationinterval')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_profile_values',
                                         through='ProfileResultValueAnnotation')

    class Meta:
        db_table = 'profileresultvalues'


class SectionResultValue(ResultValue, AggregatedComponent, XOffsetComponent, ZOffsetComponent, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('SectionResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    x_aggregation_interval = models.FloatField(db_column='xaggregationinterval')
    z_aggregation_interval = models.FloatField(db_column='zaggregationinterval')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_section_values',
                                         through='SectionResultValueAnnotation')

    class Meta:
        db_table = 'sectionresultvalues'


class SpectraResultValue(ResultValue, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('SpectraResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    excitation_wavelength = models.FloatField(db_column='excitationwavelength')
    emission_wavelength = models.FloatField(db_column='emissionwavelength')
    wavelength_unit = models.ForeignKey('Unit', db_column='wavelengthunitsid')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_spectra_values',
                                         through='SpectraResultValueAnnotation')

    class Meta:
        db_table = 'spectraresultvalues'


class TimeSeriesResultValue(ResultValue, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('TimeSeriesResult', related_name='values', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_time_series_values',
                                         through='TimeSeriesResultValueAnnotation')

    objects = TimeSeriesValuesQuerySet.as_manager()

    class Meta:
        db_table = 'timeseriesresultvalues'
        ordering = ('value_datetime', )


class TrajectoryResultValue(ResultValue, XOffsetComponent, YOffsetComponent, ZOffsetComponent, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('TrajectoryResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    trajectory_distance = models.FloatField(db_column='trajectorydistance')
    trajectory_distance_aggregation_interval = models.FloatField(db_column='trajectorydistanceaggregationinterval')
    trajectory_distance_unit = models.ForeignKey('Unit', db_column='trajectorydistanceunitsid')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_Trajectory_values',
                                         through='TrajectoryResultValueAnnotation')

    class Meta:
        db_table = 'trajectoryresultvalues'


class TransectResultValue(ResultValue, AggregatedComponent, XOffsetComponent, YOffsetComponent, QualityControlComponent, TimeAggregationComponent):
    result = models.ForeignKey('TransectResult', db_column='resultid')
    data_value = models.FloatField(db_column='datavalue')
    transect_distance = models.FloatField(db_column='transectdistance')
    transect_distance_aggregation_interval = models.FloatField(db_column='transectdistanceaggregationinterval')
    transect_distance_unit = models.ForeignKey('Unit', db_column='transectdistanceunitsid')
    annotations = models.ManyToManyField('Annotation', related_name='annotated_transect_values',
                                         through='TransectResultValueAnnotation')

    class Meta:
        db_table = 'transectresultvalues'


class MeasurementResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('MeasurementResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'measurementresultvalueannotations'


class CategoricalResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('CategoricalResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'categoricalresultvalueannotations'


class PointCoverageResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('PointCoverageResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'pointcoverageresultvalueannotations'


class ProfileResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('ProfileResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'profileresultvalueannotations'


class SectionResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('SectionResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'sectionresultvalueannotations'


class SpectraResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('SpectraResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'spectraresultvalueannotations'


class TimeSeriesResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('TimeSeriesResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'timeseriesresultvalueannotations'


class TrajectoryResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('TrajectoryResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'trajectoryresultvalueannotations'


class TransectResultValueAnnotation(ResultValueAnnotation):
    value = models.ForeignKey('TransectResultValue', related_name='+', db_column='valueid')

    class Meta:
        db_table = 'transectresultvalueannotations'

# endregion


# TODO: make something more sophisticated than this later on
sql_schema_fix = 'odm2].['   # for SQL databases
psql_schema_fix = 'odm2"."'  # for postgres databases
clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
classes = [model for name, model in clsmembers if issubclass(model, models.Model)]
database_manager = settings.DATABASES['odm2']['ENGINE']

for model in classes:
    if database_manager == u'sql_server.pyodbc':
        model._meta.db_table = sql_schema_fix.upper() + model._meta.db_table
    elif database_manager == u'django.db.backends.postgresql_psycopg2':
        model._meta.db_table = psql_schema_fix + model._meta.db_table

            # can add more fixes there depending on the database engine
