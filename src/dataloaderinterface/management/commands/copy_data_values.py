from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from dataloader.models import TimeSeriesResultValue


class Command(BaseCommand):
    help = 'Copy the data values from a production database over to a staging or testing database.'

    def add_arguments(self, parser):
        parser.add_argument('source', type=str, help='The source database name as specified in settings.json.')
        parser.add_argument('destination', type=str, help='The destination database name as specified in settings.json.')
        parser.add_argument('date', type=str, help='The starting date for the data copy in UTC time with the ISO 8601 format (%Y-%m-%dT%H:%M:%S).')

    def handle(self, *args, **options):
        source = options['source']
        destination = options['destination']
        start_date = datetime.strptime(options['date'], "%Y-%m-%dT%H:%M:%S")

        print('- Getting data values.')
        data_values = TimeSeriesResultValue.objects.using(source).filter(value_datetime__gte=start_date)
        print('- {} data values found.'.format(data_values.count()))

        for data_value in data_values:
            try:
                copied_value = TimeSeriesResultValue.objects.using(destination).create(
                    value_datetime=data_value.value_datetime,
                    value_datetime_utc_offset=data_value.value_datetime_utc_offset,
                    result_id=data_value.result_id,
                    data_value=data_value.data_value,
                    censor_code=data_value.censor_code,
                    quality_code=data_value.quality_code,
                    time_aggregation_interval=data_value.time_aggregation_interval,
                    time_aggregation_interval_unit=data_value.time_aggregation_interval_unit
                )
                print('{} - {} in result {}'.format(copied_value.pk, copied_value.value_datetime, copied_value.result_id))

            except IntegrityError as ve:
                print('already exists {} - {} in result {}'.format(data_value.pk, data_value.value_datetime, data_value.result_id))

        print('All {} values copied over to {}!'.format(source, destination))
