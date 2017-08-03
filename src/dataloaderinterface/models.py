from __future__ import unicode_literals

# Create your models here.
from django.db.models.aggregates import Min

from dataloader.models import SamplingFeature, Affiliation
from django.contrib.auth.models import User
from django.db import models


class DeviceRegistration(models.Model):
    registration_id = models.AutoField(primary_key=True, db_column='RegistrationID')
    deployment_sampling_feature_uuid = models.UUIDField(db_column='SamplingFeatureUUID')
    authentication_token = models.CharField(max_length=64, editable=False, db_column='AuthenticationToken')
    user = models.ForeignKey('ODM2User', db_column='User')
    # deployment_date = models.DateTimeField(db_column='DeploymentDate')

    def registration_date(self):
        action = self.sampling_feature.actions.first()
        return action and action.begin_datetime

    @property
    def deployment_date(self):
        sampling_feature = self.sampling_feature
        min_datetime = sampling_feature.feature_actions.aggregate(first_light=Min('results__valid_datetime'))
        return min_datetime['first_light']

    @property
    def sampling_feature(self):
        return SamplingFeature.objects.get(sampling_feature_uuid__exact=self.deployment_sampling_feature_uuid)

    def __str__(self):
        action = self.sampling_feature.actions.first()
        return '{}\t{}: {}'.format(self.sampling_feature.sampling_feature_code, action.action_type_id, action.begin_datetime.strftime('%Y/%m/%d'))


class ODM2User(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    affiliation_id = models.IntegerField()

    @property
    def affiliation(self):
        return Affiliation.objects.get(pk=self.affiliation_id)

    def can_administer_site(self, registration):
        return self.user.is_staff or registration.user == self
