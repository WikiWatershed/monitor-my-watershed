from datetime import datetime

from django.core.management import BaseCommand

from dataloader.helpers import InfluxHelper
from dataloaderinterface.models import SiteSensor


class Command(BaseCommand):
    help = 'Copy data values over to the InfluxDB instance.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            dest='clean',
            help='Drop the influx database before filling up data.',
        )

    def handle(self, *args, **options):
        recreate_database = options.get('clean')

        helper = InfluxHelper()
        helper.connect_to_dataframe_client()
        sensors = SiteSensor.objects.all()

        if recreate_database:
            helper.recreate_database()

        for sensor in sensors:
            print('- writing data to sensor {}'.format(sensor.sensor_identity))
            last_value = helper.get_series_last_value(sensor.influx_identifier)
            starting_point = last_value and last_value.replace(tzinfo=None) or datetime.min
            result = helper.write_sensor_values(sensor, starting_point)
            print('-- {} points written.'.format(result))
