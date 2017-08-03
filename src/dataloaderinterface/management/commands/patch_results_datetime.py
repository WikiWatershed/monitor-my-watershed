from django.core.management.base import BaseCommand
from django.db.models.aggregates import Count

from dataloader.models import Result


class Command(BaseCommand):
    help = ''

    @staticmethod
    def fix_results_value_count():
        results = Result.objects.annotate(number_of_values=Count('timeseriesresult__values'))
        for result in results:
            result.value_count = result.number_of_values
            result.save()


    def handle(self, *args, **options):
        self.fix_results_value_count()
        results = Result.objects.prefetch_related('timeseriesresult__values').filter(value_count__gt=0)
        for result in results:
            first_value = result.timeseriesresult.values.order_by('value_datetime').first()
            result.valid_datetime = first_value.value_datetime
            result.valid_datetime_utc_offset = first_value.value_datetime_utc_offset
            result.save()
            print('result %s: set first valid datetime to %s' % (result.pk, result.valid_datetime))
