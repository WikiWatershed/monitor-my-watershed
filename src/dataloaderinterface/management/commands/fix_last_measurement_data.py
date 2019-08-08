from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.aggregates import Min

from dataloader.models import TimeSeriesResult
from dataloaderinterface.models import SiteRegistration, SiteSensor, SensorMeasurement


class Command(BaseCommand):
    help = 'Create `Last Measurement` objects for all sensors.'

    def handle(self, *args, **options):
        print('- Getting results')
        results = TimeSeriesResult.objects.annotate(values_count=Count('values')).all()
        print('- {} results found'.format(results.count()))

        for result in results:
            sensor = SiteSensor.objects.filter(result_id=result.result_id).first()
            if not sensor:
                continue

            if not result.values_count:
                continue

            print('- creating last measurement data for {}'.format(sensor.sensor_identity))
            last_data_value = result.values.latest('value_datetime')

            last_measurement = SensorMeasurement.objects.filter(sensor=sensor).first()
            last_measurement and last_measurement.delete()

            SensorMeasurement.objects.create(
                sensor=sensor,
                value_datetime=last_data_value.value_datetime,
                value_datetime_utc_offset=timedelta(hours=last_data_value.value_datetime_utc_offset),
                data_value=last_data_value.data_value
            )
        print('- Done!')
