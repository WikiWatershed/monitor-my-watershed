from __future__ import unicode_literals

from typing import List

from django.db import models
from django.db.models.aggregates import Max
from django.db.models.expressions import F, OuterRef, Subquery, When, Value, Case
from django.db.models import expressions
from django.db.models.query import Prefetch
from django.db.models import CharField

class SiteRegistrationQuerySet(models.QuerySet):
    # TODO: put the status variables in a settings file so it's customizable.
    status_variables = ['EnviroDIY_Mayfly_Batt', 'EnviroDIY_Mayfly_Temp']

    def with_sensors(self):
        return self.prefetch_related('sensors__sensor_output')

    def with_leafpacks(self):
        return self.prefetch_related('leafpack_set')

    def with_sensors_last_measurement(self):
        return self.prefetch_related('sensors__last_measurement')

    def with_latest_measurement_id(self):
        sensor_model = [
            related_object.related_model
            for related_object in self.model._meta.related_objects
            if related_object.name == 'sensors'
        ].pop()

        # lol i can't believe this worked
        query = sensor_model.objects.filter(registration=OuterRef('pk')).order_by('-last_measurement__value_datetime')
        return self.prefetch_related('sensors__last_measurement').annotate(
            latest_measurement_id=Subquery(query.values('last_measurement')[:1]),
        )

    def with_status_sensors(self):
        # gets the SiteSensor class from the SiteRegistration model to avoid a circular import
        # don't try this at home, kids.
        sensor_model = [
            related_object.related_model
            for related_object in self.model._meta.related_objects
            if related_object.name == 'sensors'
        ].pop()

        return self.prefetch_related(Prefetch(
            lookup='sensors',
            queryset=sensor_model.objects.filter(sensor_output__variable_code__in=self.status_variables),
            to_attr='status_sensors'))

    def with_ownership_status(self, user_id:int, affiliation_ids:List[int]):
        return self.annotate(ownership_status=Case(
            When(organization_id__in=affiliation_ids, then=Value('owned')),
            When(followed_by=user_id, then=Value('followed')),
            default=Value('unfollowed'),
            output_field=CharField(),
        ))
 
    def deployed_by(self, organization_ids:List[int]):
        return self.filter(organization_id__in=organization_ids)

    def followed_by(self, user_id):
        return self.filter(followed_by=user_id)


class SiteSensorQuerySet(models.QuerySet):
    pass


class SensorOutputQuerySet(models.QuerySet):
    def with_filter_names(self):
        return self.annotate(
            sensor_manufacturer=F('model_manufacturer'),
            sensor_model=F('model_id'),
            variable=F('variable_id'),
            unit=F('unit_id')
        )

    def for_filters(self):
        return self.with_filter_names().values(
            'pk',
            'sensor_manufacturer',
            'sensor_model',
            'variable',
            'unit',
            'sampled_medium'
        )
