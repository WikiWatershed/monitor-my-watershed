# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from django.db import models
from django.contrib.auth.models import AbstractUser

from dataloader.models import Affiliation


#class User(AbstractUser):
#    affiliation_id = models.IntegerField(null=True)  # Temporarily nullable
#    email = models.EmailField(max_length=255, unique=True, blank=False)
#    organization_code = models.CharField(max_length=51, blank=True, null=True)
#    organization_name = models.CharField(max_length=256, blank=True, null=True)
#
#    @property
#    def affiliation(self):
#        return Affiliation.objects.get(pk=self.affiliation_id)
#
#    def owns_site(self, registration):
#        return registration.django_user == self
#
#    def can_administer_site(self, registration):
#        return self.is_staff or registration.django_user == self
#
#    class Meta:
#        db_table = 'auth_user'
#