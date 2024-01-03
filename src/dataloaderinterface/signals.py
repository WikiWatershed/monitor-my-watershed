from datetime import datetime

from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch.dispatcher import receiver

from dataloader.models import SamplingFeature, Site, Annotation, SamplingFeatureAnnotation, SpatialReference, Action, \
    Method, Result, ProcessingLevel, TimeSeriesResult, Unit, Affiliation
from dataloaderinterface.models import SiteRegistration, SiteSensor

#PRT - deprecated
#from tsa.helpers import TimeSeriesAnalystHelper

import accounts


@receiver(pre_save, sender=SiteRegistration)
def handle_site_registration_pre_save(sender, instance, update_fields=None, **kwargs):
    if not instance.pk:
        sampling_feature = SamplingFeature.objects.create(
            sampling_feature_type_id='Site',
            sampling_feature_code=instance.sampling_feature_code,
            sampling_feature_name=instance.sampling_feature_name,
            elevation_m=instance.elevation_m,
            elevation_datum_id=instance.elevation_datum
        )
        instance.sampling_feature_id = sampling_feature.sampling_feature_id

    user = None
    if hasattr(instance, 'user'): 
        user = instance.user
    else: 
        user = accounts.user.ODM2User.from_userid(instance.account_id.accountid)
    
    #use the selected affiliation to look up organization
    affiliation = Affiliation.objects.get(pk=instance.affiliation_id)
    
    instance.account_id = accounts.models.Account.objects.get(pk=user.user_id)
    instance.person_id = -999 #PRT - deprecated the use of person with accounts update   
    instance.person_first_name = user.first_name
    instance.person_last_name = user.last_name
    instance.organization_id = affiliation.organization_id


@receiver(post_save, sender=SiteRegistration)
def handle_site_registration_post_save(sender, instance, created, update_fields=None, **kwargs):
    sampling_feature = instance.sampling_feature

    if created:
        Site.objects.create(
            sampling_feature=sampling_feature,
            site_type_id=instance.site_type,
            latitude=instance.latitude,
            longitude=instance.longitude,
            spatial_reference=SpatialReference.objects.get(srs_name='WGS84')
        )

        stream_name = Annotation(annotation_type_id='Sampling feature annotation', annotation_code='stream_name', annotation_text=instance.stream_name or '')
        major_watershed = Annotation(annotation_type_id='Sampling feature annotation', annotation_code='major_watershed', annotation_text=instance.major_watershed or '')
        sub_basin = Annotation(annotation_type_id='Sampling feature annotation', annotation_code='sub_basin', annotation_text=instance.sub_basin or '')
        closest_town = Annotation(annotation_type_id='Sampling feature annotation', annotation_code='closest_town', annotation_text=instance.closest_town or '')
        Annotation.objects.bulk_create([stream_name, major_watershed, sub_basin, closest_town])

        SamplingFeatureAnnotation.objects.bulk_create([
            SamplingFeatureAnnotation(annotation=stream_name, sampling_feature=sampling_feature),
            SamplingFeatureAnnotation(annotation=major_watershed, sampling_feature=sampling_feature),
            SamplingFeatureAnnotation(annotation=sub_basin, sampling_feature=sampling_feature),
            SamplingFeatureAnnotation(annotation=closest_town, sampling_feature=sampling_feature)
        ])

    else:
        SamplingFeature.objects.filter(pk=instance.sampling_feature_id).update(
            sampling_feature_code=instance.sampling_feature_code,
            sampling_feature_name=instance.sampling_feature_name,
            elevation_m=instance.elevation_m,
            elevation_datum_id=instance.elevation_datum
        )

        Site.objects.filter(pk=instance.sampling_feature_id).update(
            site_type_id=instance.site_type,
            latitude=instance.latitude,
            longitude=instance.longitude
        )

        sampling_feature.annotations.filter(annotation_code='stream_name').update(annotation_text=instance.stream_name or '')
        sampling_feature.annotations.filter(annotation_code='major_watershed').update(annotation_text=instance.major_watershed or '')
        sampling_feature.annotations.filter(annotation_code='sub_basin').update(annotation_text=instance.sub_basin or '')
        sampling_feature.annotations.filter(annotation_code='closest_town').update(annotation_text=instance.closest_town or '')


#PRT - deprecated
#@receiver(post_save, sender=SiteRegistration)
#def handle_site_registration_tsa_post_save(sender, instance, created, update_fields=None, **kwargs):
#    if created:
#        return
#    helper = TimeSeriesAnalystHelper()
#    helper.update_series_from_site(instance)


@receiver(post_delete, sender=SiteRegistration)
def handle_site_registration_post_delete(sender, instance, **kwargs):
    sampling_feature = instance.sampling_feature
    if not sampling_feature:
        return
    sampling_feature.annotations.all().delete()
    sampling_feature and sampling_feature.delete()


@receiver(pre_save, sender=SiteSensor)
def handle_sensor_pre_save(sender, instance, update_fields=None, **kwargs):
    if instance.pk:
        return

    action = Action.objects.create(
        method=Method.objects.filter(method_type_id='Instrument deployment').first(),
        action_type_id='Instrument deployment',
        begin_datetime=datetime.utcnow(), begin_datetime_utc_offset=0
    )
    feature_action = action.feature_actions.create(sampling_feature=instance.registration.sampling_feature)

    result = Result.objects.create(
        feature_action=feature_action,
        result_type_id='Time series coverage',
        variable_id=instance.sensor_output.variable_id,
        unit_id=instance.sensor_output.unit_id,
        processing_level=ProcessingLevel.objects.filter(processing_level_code='Raw').first(),
        sampled_medium_id=instance.sensor_output.sampled_medium,
        status_id='Ongoing'
    )

    instance.result_id = result.result_id
    instance.result_uuid = result.result_uuid


@receiver(post_save, sender=SiteSensor)
def handle_sensor_post_save(sender, instance, created, update_fields=None, **kwargs):
    action = instance.registration.sampling_feature.actions.first()
    result_queryset = Result.objects.filter(result_id=instance.result_id)

    if created:
        action.action_by.create(affiliation=instance.registration.odm2_affiliation, is_action_lead=True)
        TimeSeriesResult.objects.create(
            result=result_queryset.first(),
            aggregation_statistic_id='Average',
            z_location=instance.height,
            z_location_unit=Unit.objects.filter(unit_name='meter').first()
        )

    else:
        result_queryset.update(
            variable_id=instance.sensor_output.variable_id,
            unit_id=instance.sensor_output.unit_id,
            sampled_medium_id=instance.sensor_output.sampled_medium
        )
        TimeSeriesResult.objects.filter(result_id=instance.result_id).update(z_location=instance.height)


#PRT - deprecated
#@receiver(post_save, sender=SiteSensor)
#def handle_sensor_tsa_post_save(sender, instance, created, update_fields=None, **kwargs):
#    helper = TimeSeriesAnalystHelper()
#    if created:
#        helper.create_series_from_sensor(instance)
#    else:
#        helper.update_series_from_sensor(instance)


@receiver(post_delete, sender=SiteSensor)
def handle_sensor_post_delete(sender, instance, **kwargs):
    result = instance.result
    result and result.feature_action.action.delete()


#PRT - deprecated
#@receiver(post_delete, sender=SiteSensor)
#def handle_sensor_tsa_post_delete(sender, instance, **kwargs):
#    helper = TimeSeriesAnalystHelper()
#    helper.delete_series_for_sensor(instance)
