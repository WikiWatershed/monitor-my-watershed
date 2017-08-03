import codecs
import csv
import os

from datetime import timedelta
from django.contrib.staticfiles.storage import staticfiles_storage
from unicodecsv.py2 import UnicodeWriter


class SiteResultSerializer:
    headers = ('DateTime', 'TimeOffset', 'DateTimeUTC', 'Value', 'CensorCode', 'QualifierCode', )
    date_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self, result):
        self.result = result

    def get_file_path(self):
        filename = "{0}_{1}_{2}.csv".format(self.result.feature_action.sampling_feature.sampling_feature_code, self.result.variable.variable_code, self.result.result_id)
        return os.path.join('data', filename)

    def open_csv_file(self):
        csv_file = staticfiles_storage.open(self.get_file_path(), 'ab+')
        return csv_file

    def get_metadata_template(self):
        with codecs.open(os.path.join(os.path.dirname(__file__), 'metadata_template.txt'), 'r', encoding='utf-8') as metadata_file:
            return metadata_file.read()

    def generate_metadata(self):
        action = self.result.feature_action.action
        equipment_model = self.result.data_logger_file_columns.first().instrument_output_variable.model
        affiliation = action.action_by.filter(is_action_lead=True).first().affiliation
        return self.get_metadata_template().format(
            sampling_feature=self.result.feature_action.sampling_feature,
            variable=self.result.variable,
            unit=self.result.unit,
            model=equipment_model,
            result=self.result,
            action=action,
            affiliation=affiliation
        ).encode('utf-8')

    def build_csv(self):
        with self.open_csv_file() as output_file:
            output_file.write(self.generate_metadata())
            csv_writer = UnicodeWriter(output_file)
            csv_writer.writerow(self.headers)

    def add_data_value(self, data_value):
        self.add_data_values([data_value])

    def add_data_values(self, data_values):
        data = [(data_value.value_datetime.strftime(self.date_format),
                 '{0}:00'.format(data_value.value_datetime_utc_offset),
                 (data_value.value_datetime - timedelta(hours=data_value.value_datetime_utc_offset)).strftime(self.date_format),
                 data_value.data_value,
                 data_value.censor_code_id,
                 data_value.quality_code_id)
                for data_value in data_values]
        with self.open_csv_file() as output_file:
            csv_writer = UnicodeWriter(output_file)
            csv_writer.writerows(data)
