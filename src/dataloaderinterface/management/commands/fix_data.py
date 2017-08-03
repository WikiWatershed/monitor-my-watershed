
from dataloader.models import DataLoggerProgramFile, DataLoggerFile, ActionBy, TimeSeriesResult, DataLoggerFileColumn, \
    InstrumentOutputVariable, Result
from django.core.management.base import BaseCommand

from dataloaderinterface.models import DeviceRegistration


class Command(BaseCommand):
    help = 'Fix corrupted or incomplete odm2 data in the scope of this application.'

    @staticmethod
    def guess_equipment_model(result):
        return InstrumentOutputVariable.objects.filter(variable=result.variable, instrument_raw_output_unit=result.unit).first()

    @staticmethod
    def check_sampling_feature(registration):
        sampling_feature = registration.sampling_feature
        if sampling_feature.feature_actions.count() == 0:
            # site doesn't have any sensors. delete site and registration.

            data_logger_program = DataLoggerProgramFile.filter(
                affiliation=registration.user.affiliation,
                program_name='%s' % sampling_feature.sampling_feature_code
            ).all()

            data_logger_file = DataLoggerFile.filter(
                program=data_logger_program,
                data_logger_file_name='%s' % sampling_feature.sampling_feature_code
            ).all()

            # TODO: columns.

            print("* site doesn't have any sensors. deleting.")
            sampling_feature.site and sampling_feature.site.delete()
            print("- site instance deleted.")
            sampling_feature.delete()
            print("- sampling feature instance deleted.")
            registration.delete()
            print("- registration instance deleted.")

    @staticmethod
    def delete_entire_registration():
        pass

    def handle(self, *args, **options):
        registrations = DeviceRegistration.objects.all()
        print("%s site registrations found." % registrations.count())
        print("----------------------------------------------------")

        for registration in registrations:
            if not registration.user and registration.user.affiliation and registration.sampling_feature:
                # doesn't have an affiliation or sampling feature. no way of fixing this.
                print("* unrepairable registration found. deleting." % registration)
                registration.delete()
                continue

            affiliation = registration.user.affiliation
            sampling_feature = registration.sampling_feature
            print("---- retrieving registration for site %s, deployment by %s." % (sampling_feature, affiliation))

            if sampling_feature.feature_actions.count() == 0:
                # site doesn't have any sensors. delete site and registration.
                print("* site doesn't have any sensors. deleting.")
                sampling_feature.site and sampling_feature.site.delete()
                print("- site instance deleted.")
                sampling_feature.delete()
                print("- sampling feature instance deleted.")
                registration.delete()
                print("- registration instance deleted.")
                continue

            data_logger_program, created = DataLoggerProgramFile.objects.get_or_create(
                affiliation=affiliation,
                program_name='%s' % sampling_feature.sampling_feature_code
            )
            print("- data logger program found for this site." if not created else "* no data logger program found for this site. creating.")

            data_logger_file, created = DataLoggerFile.objects.get_or_create(
                program=data_logger_program,
                data_logger_file_name='%s' % sampling_feature.sampling_feature_code
            )
            print("- data logger file found for this site." if not created else "* no data logger file found for this site. creating.")

            print("-- loading feature actions")
            for feature_action in sampling_feature.feature_actions.all():
                result = feature_action.results.first()
                action = feature_action.action

                if not result:
                    print("* feature action has no associated result. deleting.")
                    feature_action.delete()
                    print("- feature action instance deleted.")
                    action.action_by and action.action_by.all().delete()
                    print("- action by instance deleted.")
                    action.delete()
                    print("- action instance deleted.")
                    continue

                print("- retrieving result %s." % result)
                action = feature_action.action
                action_by, created = ActionBy.objects.get_or_create(action=action, affiliation=affiliation, is_action_lead=True)
                print("- action by instance found." if not created else "* action by instance not found. creating.")

                time_series_result, created = TimeSeriesResult.objects.get_or_create(
                    result=result,
                    aggregation_statistic_id='Average',
                )
                print("- time series result instance found." if not created else "* no time series result instance found for this site. creating.")

                column = result.data_logger_file_columns.first()
                column_label = '%s(%s)' % (result.variable.variable_code, result.unit.unit_abbreviation)
                if not column:
                    print("* no data logger file column associated with this result. creating.")
                    DataLoggerFileColumn.objects.create(
                        result=result,
                        data_logger_file=data_logger_file,
                        instrument_output_variable=self.guess_equipment_model(result),
                        column_label=column_label
                    )
                else:
                    if column.data_logger_file != data_logger_file:
                        print("* data logger column doesn't belong to retrieved data logger file. matching up.")
                        column.data_logger_file = data_logger_file
                        column.save()
                    if column.column_label != column_label:
                        column.column_label = column_label
                        column.save()

                    # data_logger_file_column = result.data_logger_file_columns.first()
                    # data_logger_file_column.instrument_output_variable = instrument_output_variable
                    # data_logger_file_column.column_label = '%s(%s)' % (
                    # result.variable.variable_code, result.unit.unit_abbreviation)

            if sampling_feature.feature_actions.count() == 0:
                # TODO: delete sampling feature.
                pass

        # Remove rogue Time Series Results.
        site_registrations = [str(uuid['deployment_sampling_feature_uuid']) for uuid in DeviceRegistration.objects.all().values('deployment_sampling_feature_uuid')]
        rogue_results = Result.objects.exclude(feature_action__sampling_feature__sampling_feature_uuid__in=(site_registrations))
        for rogue_result in rogue_results:
            rogue_result.timeseriesresult and rogue_result.timeseriesresult.values.all().delete()
            rogue_result.timeseriesresult and rogue_result.timeseriesresult.delete()
            rogue_result.delete()


        print("check complete!")
