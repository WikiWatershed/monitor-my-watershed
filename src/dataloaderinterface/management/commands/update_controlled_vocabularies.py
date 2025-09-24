
import requests
from django.core.management.base import BaseCommand

from dataloader.models import ActionType, AggregationStatistic, AnnotationType, CensorCode, DataQualityType, \
    DataSetType, DirectiveType, ElevationDatum, EquipmentType, Medium, MethodType, OrganizationType, PropertyDataType, \
    QualityCode, RelationshipType, ResultType, SamplingFeatureGeoType, SamplingFeatureType, SiteType, SpatialOffsetType, \
    Speciation, SpecimenType, Status, TaxonomicClassifierType, UnitsType, VariableName, VariableType

vocabularies_map = {
        'actiontype': ActionType,
        'aggregationstatistic': AggregationStatistic,
        'annotationtype': AnnotationType,
        'censorcode': CensorCode,
        'dataqualitytype': DataQualityType,
        # 'datasettype': DataSetType,
        'directivetype': DirectiveType,
        'elevationdatum': ElevationDatum,
        'equipmenttype': EquipmentType,
        'medium': Medium,
        'methodtype': MethodType,
        'organizationtype': OrganizationType,
        'propertydatatype': PropertyDataType,
        'qualitycode': QualityCode,
        'relationshiptype': RelationshipType,
        'resulttype': ResultType,
        'samplingfeaturegeotype': SamplingFeatureGeoType,
        'samplingfeaturetype': SamplingFeatureType,
        'sitetype': SiteType,
        'spatialoffsettype': SpatialOffsetType,
        'speciation': Speciation,
        'specimentype': SpecimenType,
        'status': Status,
        'taxonomicclassifiertype': TaxonomicClassifierType,
        'unitstype': UnitsType,
        'variablename': VariableName,
        'variabletype': VariableType
    }


class Command(BaseCommand):
    help = 'Update the ODM2 Controlled Vocabularies tables with the CVs in vocabulary.odm2.org'

    def handle(self, *args, **options):
        # TODO: These values should go in the settings.json file and not hardcoded.
        base_url = 'http://vocabulary.odm2.org'
        api_url = '/api/v1'
        request_uri = '%s%s/{cv}/?format=json' % (base_url, api_url)

        for cv_name in vocabularies_map.keys():
            vocabulary_model = vocabularies_map[cv_name]
            print('Getting %s vocabulary' % vocabulary_model._meta.verbose_name)

            request = requests.get(request_uri.format(cv=cv_name))
            response = request.json()

            if request.status_code != 200:
                print('- Error %s getting %s controlled vocabularies' % (request.status_code, vocabulary_model._meta.verbose_name))
                continue
            if 'objects' not in response:
                print('- Error: The server didn\'t result a list of objects.')
                continue

            to_add = [concept for concept in response['objects'] if (concept['name'],) not in vocabulary_model.objects.values_list('name')]
            if not len(to_add):
                print('- Nothing to add here.')
                continue

            # remove duplicates to avoid the database insert failing due
            # to a unique constraint violation
            seen_names = set()
            deduplicated_add = []
            for concept in response['objects']:
                if concept['name'] not in seen_names:
                    seen_names.add(concept['name'])
                    deduplicated_add.append(concept)
            to_add = deduplicated_add

            vocabulary_objects = [vocabulary_model(
                term=vocabulary['term'],
                name=vocabulary['name'],
                definition=vocabulary['definition'],
                category=vocabulary['category'],
                source_vocabulary_uri=vocabulary['resource_uri'].replace(api_url, base_url)
            ) for vocabulary in to_add]

            created = vocabulary_model.objects.bulk_create(vocabulary_objects)
            print('- %s entried added to the %s vocabulary' % (len(created), vocabulary_model._meta.verbose_name))
