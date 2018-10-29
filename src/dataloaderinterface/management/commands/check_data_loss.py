from datetime import datetime, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import ExpressionWrapper, F, DurationField, Q
from django.db.models.aggregates import Max
from django.core.mail import send_mail

from dataloaderinterface.models import SiteAlert


class Command(BaseCommand):
    help = ''

    @staticmethod
    def send_email(email_address, subject, message):
        print("- sending email to {}: {}".format(email_address, subject))
        success = send_mail(subject, message, settings.NOTIFY_EMAIL_SENDER, [email_address])
        return success == 1

    def handle(self, *args, **options):
        # MAGICAL BEAUTIFUL QUERY
        all_site_alerts = SiteAlert.objects \
            .prefetch_related('site_registration__sensors__last_measurement', 'user') \
            .annotate(last_measurement_datetime=Max('site_registration__sensors__last_measurement__value_datetime')) \
            .filter(last_measurement_datetime__isnull=False) \
            .annotate(data_gap=ExpressionWrapper(datetime.utcnow() - F('last_measurement_datetime'), output_field=DurationField())) \
            .filter(Q(last_alerted__isnull=True) | Q(last_measurement_datetime__gt=F('last_alerted')), data_gap__gte=F('hours_threshold'))

        print("{} site alerts found.".format(all_site_alerts.count()))
        for site_alert in all_site_alerts:
            gap = int(site_alert.data_gap.total_seconds() / 3600)

            subject = 'EnviroDIY Notification: No data received for site' \
                      ' {} in the last {} hours'.format(site_alert.site_registration.sampling_feature_name, gap)

            message = ("{},\n\n"
                       "This email is to notify you that your EnviroDIY site \"{}\" has not received any new "
                       "data values in the last {} hours. The last update was on {}. You may want to check your "
                       "equipment to ensure it's working as intended. \n\n"
                       "https://data.envirodiy.org/sites/{}/\n\n"
                       "Best regards,\n"
                       "The EnviroDIY team.\n"
                       "").format(site_alert.user.first_name, site_alert.site_registration.sampling_feature_name,
                                  gap, site_alert.last_measurement_datetime,
                                  site_alert.site_registration.sampling_feature_code)
            success = Command.send_email(site_alert.user.email, subject, message)
            if success:
                site_alert.last_alerted = datetime.utcnow()
                site_alert.save()
