from django.core.management.base import BaseCommand

from dataloader.models import Result, TimeSeriesResult
from dataloaderinterface.csv_serializer import SiteResultSerializer


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        results = TimeSeriesResult.objects.prefetch_related(
            'result__variable',
            'result__unit',
            'result__processing_level',
            'result__data_logger_file_columns__instrument_output_variable__model',
            'result__feature_action__sampling_feature__site',
            'result__feature_action__action__method',
            'result__feature_action__action__action_by__affiliation__person',
            'result__feature_action__action__action_by__affiliation__organization'
        ).all()
        for time_series_result in results:
            print('result %s:' % time_series_result.result_id)
            serializer = SiteResultSerializer(result=time_series_result.result)
            serializer.build_csv()
            print('-file with metadata created')
            if time_series_result.result.value_count > 0:
                values = time_series_result.values.all()
                serializer.add_data_values(values)
                print('-data values written to file')

            print('--csv generated.')
