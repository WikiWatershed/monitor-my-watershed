from django.core.management.base import BaseCommand

from dataloader.models import InstrumentOutputVariable
from dataloaderinterface.forms import SiteSensorForm
from dataloaderinterface.models import SensorOutput


class Command(BaseCommand):
    help = ''

    def handle(self, *args, **options):
        sampled_media = SiteSensorForm.allowed_sampled_medium
        instrument_output_variables = InstrumentOutputVariable.objects.all()
        output_variables_count = instrument_output_variables.count()
        print('{} instrument output variables found.'.format(output_variables_count))
        print('Max number of sensor output variables to generate: {}'.format(output_variables_count * len(sampled_media)))
        print('...')
        counter = 0
        for instrument_output_variable in instrument_output_variables:
            print('--creating data for {}'.format(instrument_output_variable))
            for sampled_medium in sampled_media:
                output, created = SensorOutput.objects.get_or_create(
                    instrument_output_variable_id=instrument_output_variable.pk,
                    model_id=instrument_output_variable.model.equipment_model_id,
                    model_name=instrument_output_variable.model.model_name,
                    model_manufacturer=instrument_output_variable.model.model_manufacturer.organization_code,
                    variable_id=instrument_output_variable.variable.variable_id,
                    variable_name=instrument_output_variable.variable.variable_name_id,
                    variable_code=instrument_output_variable.variable.variable_code,
                    unit_id=instrument_output_variable.instrument_raw_output_unit.unit_id,
                    unit_name=instrument_output_variable.instrument_raw_output_unit.unit_name,
                    unit_abbreviation=instrument_output_variable.instrument_raw_output_unit.unit_abbreviation,
                    sampled_medium=sampled_medium
                )
                print('-{}: {}'.format('created' if created else 'not created', counter))
                counter += 1
        print('Done!')
