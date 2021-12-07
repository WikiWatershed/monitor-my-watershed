# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta, datetime

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db import models
from django.conf import settings
# from django.core.exceptions import ValidationError

from dataloaderinterface.models import SiteRegistration

HYDROSHARE_SYNC_TYPES = (('M', 'Manual'), ('S', 'Scheduled'))


class OAuthToken(models.Model):
    access_token = models.CharField(max_length=255)
    refresh_token = models.CharField(max_length=255)
    token_type = models.CharField(max_length=len('Bearer'), default='Bearer', editable=False)
    expires_in = models.DateTimeField(default=timezone.now)
    scope = models.CharField(max_length=255, default='read')

    @property
    def is_expired(self):
        return datetime.today() > self.expires_in

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if isinstance(self.expires_in, str):
            self.expires_in = int(self.expires_in)

        if isinstance(self.expires_in, int):
            self.expires_in = datetime.today() + timedelta(seconds=self.expires_in)

        super(OAuthToken, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                     update_fields=update_fields)

    def to_dict(self):
        token = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_type': self.token_type,
            'expires_in': int((self.expires_in - timezone.now()).total_seconds()),
            'scope': self.scope
        }
        return token

    class Meta:
        db_table = 'oauth_token'


# HSUAccount - holds information for user's Hydroshare account
class HydroShareAccount(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='hydroshare_account', on_delete=models.CASCADE)
    is_enabled = models.BooleanField(default=False)
    ext_id = models.IntegerField(unique=True)  # external hydroshare account id
    token = models.ForeignKey(OAuthToken, db_column='token_id', null=True, on_delete=models.CASCADE)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        return super(HydroShareAccount, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                                   update_fields=update_fields)

    def delete(self, using=None, **kwargs):
        return super(HydroShareAccount, self).delete(using=using, keep_parents=True)

    @property
    def username(self):
        return self.user.username
        # return ODM2User.objects.filter(hydroshare_account=self.pk).first().user.username

    def resources(self):
        return ", ".join([str(r.id) for r in HydroShareResource.objects.filter(hs_account=self)])
    resources.short_description = 'Resource IDs'

    def get_token(self):
        try:
            return self.token.to_dict()
        except ObjectDoesNotExist:
            return None

    def update_token(self, token_dict):  # type: (dict) -> None
        if isinstance(self.token, OAuthToken):
            self.token.access_token = token_dict.get('access_token')
            self.token.refresh_token = token_dict.get('refresh_token')
            self.token.token_type = token_dict.get('token_type')
            self.token.expires_in = token_dict.get('expires_in')
            self.token.scope = token_dict.get('scope')
            self.token.save()
        self.save()

    def to_dict(self, include_token=True):
        account = {
            'id': self.pk,
            'ext_id': self.ext_id,
            'is_enabled': self.is_enabled
        }
        if include_token:
            token = self.get_token()
            if token:
                account['token'] = token
        return account

    class Meta:
        db_table = 'hydroshare_account'


# "Settings" for a Hydroshare account connection
class HydroShareResource(models.Model):
    SYNC_TYPES = ['scheduled', 'manual']
    FREQUENCY_CHOICES = (
        (timedelta(), 'never'),
        (timedelta(minutes=1), 'minute'),
        (timedelta(days=1).total_seconds(), 'daily'),
        (timedelta(weeks=1).total_seconds(), 'weekly'),
        (timedelta(days=30).total_seconds(), 'monthly')
    )

    hs_account = models.ForeignKey(HydroShareAccount, db_column='hs_account_id', on_delete=models.CASCADE, null=True,
                                   blank=True)
    ext_id = models.CharField(max_length=255, blank=True, null=True, unique=True)  # external hydroshare resource id
    site_registration = models.OneToOneField(SiteRegistration, related_name='hydroshare_resource', on_delete=models.CASCADE)
    sync_type = models.CharField(max_length=255, default='manual', choices=HYDROSHARE_SYNC_TYPES)
    update_freq = models.CharField(max_length=32, verbose_name='Update Frequency', default='daily')
    is_enabled = models.BooleanField(default=True)
    last_sync_date = models.DateTimeField(auto_created=True)
    data_types = models.CharField(max_length=255, blank=True, default='')
    visible = models.BooleanField(default=True)
    title = models.CharField(default='', blank=True, null=True, max_length=255)

    @property
    def sync_type_verbose(self):
        return 'Scheduled' if self.sync_type == 'S' else 'Manual'

    @property
    def update_freq_verbose(self):
        for choice in HydroShareResource.FREQUENCY_CHOICES:
            if choice[0] == self.update_freq.total_seconds():
                return choice[1]
        return 'NA'

    @property
    def next_sync_date(self):
        date = self.get_next_sync_date()
        if isinstance(date, datetime):
            return date.replace(hour=5, minute=0)
        return self.get_next_sync_date()

    @property
    def sync_at_hour(self):
        """
        :returns a string representation of the hour that files for this resource will sync at. For example, if
        sync_at_hour equals '5', then this resource will sync at 5:00 AM on days the resource fils are synced with
        hydroshare.org.
        """
        return str(settings.CRONTAB_EXECUTE_DAILY_AT_HOUR)

    def get_udpate_freq_index(self):
        try:
            return [choice[0] for choice in HydroShareResource.FREQUENCY_CHOICES].index(self.update_freq.total_seconds())
        except Exception:
            return 0

    def get_next_sync_date(self):
        days = 0
        minutes = 0
        if self.update_freq == 'minute':
            minutes = 1
        if self.update_freq == 'daily':
            days = 1
        elif self.update_freq == 'weekly':
            days = 7
        elif self.update_freq == 'monthly':
            days = 30

        if isinstance(self.last_sync_date, datetime):
            date = self.last_sync_date
        else:
            date = datetime.combine(self.last_sync_date.date(), datetime.min.time())

        return date + timedelta(days=days, minutes=minutes)

    def to_dict(self):
        return {
            'id': self.pk,
            'hs_account': self.hs_account.id,
            'site_registration': self.site_registration.registration_id,
            'sync_type': self.sync_type,
            'update_freq': self.update_freq,
            'is_enabled': self.is_enabled,
            'last_sync_date': self.last_sync_date,
            'data_types': self.data_types.split(",")
        }

    def __str__(self):
        return '<HydroShareResource: {}>'.format(self.pk)

    def __unicode__(self):
        return self.title if self.title is not None else self.ext_id

    class Meta:
        db_table = 'hydroshare_resource'
