from datetime import timedelta
from django.core.management.base import BaseCommand

from dataloaderinterface.models import SiteSensor


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        sensors = SiteSensor.objects.filter(last_measurement_datetime__isnull=False)
        for sensor in sensors:
            sensor.last_measurement_utc_datetime = sensor.last_measurement_datetime - timedelta(hours=sensor.last_measurement_utc_offset)
            sensor.save(update_fields=['last_measurement_utc_datetime'])
            print('Last measurement utc datetime added to all sensors.')
