from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.dispatch.dispatcher import receiver

from dataloader.models import People, Organization, Affiliation


@receiver(pre_save, sender=settings.AUTH_USER_MODEL)
def handle_user_pre_save(sender, instance, update_fields=None, **kwargs):
    if not instance.pk:
        person = People.objects.create(person_first_name=instance.first_name, person_last_name=instance.last_name)
        organization = Organization.objects.filter(organization_code=instance.organization_code).first()
        affiliation = Affiliation.objects.create(
            person=person,
            organization=organization,
            affiliation_start_date=datetime.utcnow(),
            primary_email=instance.email
        )
        instance.affiliation_id = affiliation.affiliation_id
        if organization is not None:
            instance.organization_name =organization.organization_name
    elif update_fields and 'organization_code' in update_fields:
        organization = Organization.objects.filter(organization_code=instance.organization_code).first()
        sender.objects.filter(pk=instance.pk).update(organization_name=organization.organization_name)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def handle_user_post_save(sender, instance, created, update_fields, **kwargs):
    if not created:
        update_fields = update_fields or []
        fields_for_odm2 = ['first_name', 'last_name', 'email', 'organization_code']

        if any((True for field in update_fields if field in fields_for_odm2)):
            organization = Organization.objects.filter(organization_code=instance.organization_code).first()
            affiliation = instance.affiliation
            person = affiliation.person
            person.person_first_name = instance.first_name
            person.person_last_name = instance.last_name
            affiliation.primary_email = instance.email
            affiliation.organization = organization

            person.save()
            affiliation.save()
