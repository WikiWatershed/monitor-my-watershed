from dataloader.models import *
from django.test import TestCase

from dataloader.tests.data import data_manager

models_data = data_manager.test_data['models']['data']


class TestSamplingFeature(TestCase):
    @staticmethod
    def create_site_sampling_feature():
        sampling_feature_type = SamplingFeatureType(**models_data['site_sampling_feature_type'])
        sampling_feature = SamplingFeature(**models_data['site_sampling_feature'])
        sampling_feature.sampling_feature_type = sampling_feature_type
        return sampling_feature

    def setUp(self):
        self.sampling_feature = self.create_site_sampling_feature()

    def test_string_representation(self):
        self.assertEqual(str(self.sampling_feature), 'Site: RB_KF_C Knowlton Fork Climate')
        self.assertEqual(self.sampling_feature.__unicode__(), u'Site: RB_KF_C Knowlton Fork Climate')


class TestAction(TestCase):
    @staticmethod
    def create_visit_action():
        method = TestMethod.create_visit_method()
        action_type = ActionType(**models_data['visit_action_type'])
        action = Action(**models_data['visit_action'])
        action.action_type = action_type
        action.method = method
        return action

    def setUp(self):
        self.action = self.create_visit_action()

    def test_string_representation(self):
        self.assertEqual(str(self.action), 'Site Visit - 1991-08-17 1:20 -7')
        self.assertEqual(self.action.__unicode__(), u'Site Visit - 1991-08-17 1:20 -7')


class TestFeatureAction(TestCase):
    @staticmethod
    def create_site_visit_feature_action():
        site_visit = TestAction.create_visit_action()
        site = TestSamplingFeature.create_site_sampling_feature()
        feature_action = FeatureAction(action=site_visit, sampling_feature=site)
        return feature_action

    def setUp(self):
        self.feature_action = self.create_site_visit_feature_action()

    def test_string_representation(self):
        self.assertEqual(str(self.feature_action), 'Site Visit - 1991-08-17 1:20 -7 RB_KF_C (Site)')
        self.assertEqual(self.feature_action.__unicode__(), u'Site Visit - 1991-08-17 1:20 -7 RB_KF_C (Site)')


class TestPeople(TestCase):
    @staticmethod
    def create_person():
        #  1. be God
        #  2. grab some dirt
        #  3. blow on it (???)
        #  4. profit!

        person = People(**models_data['person'])
        return person

    def setUp(self):
        self.person = self.create_person()

    def test_string_representation(self):
        self.assertEqual(str(self.person), 'Jeffery Horsburgh')
        self.assertEqual(self.person.__unicode__(), u'Jeffery Horsburgh')


class TestOrganization(TestCase):
    @staticmethod
    def create_usu_organization():
        organization_type = OrganizationType(**models_data['research_organization_type'])
        organization = Organization(**models_data['usu_organization'])
        organization.organization_type = organization_type
        return organization

    def setUp(self):
        self.organization = self.create_usu_organization()

    def test_string_representation(self):
        self.assertEqual(str(self.organization), 'Research institute: Utah State University')
        self.assertEqual(self.organization.__unicode__(), u'Research institute: Utah State University')


class TestAffiliation(TestCase):
    @staticmethod
    def create_usu_affiliation():
        person = TestPeople.create_person()
        organization = TestOrganization.create_usu_organization()
        affiliation = Affiliation(**models_data['usu_affiliation'])
        affiliation.organization = organization
        affiliation.person = person
        return affiliation

    def setUp(self):
        self.affiliation = self.create_usu_affiliation()

    def test_string_representation(self):
        self.assertEqual(str(self.affiliation), 'Jeffery Horsburgh (Utah State University) - serious.email@usu.edu')
        self.assertEqual(self.affiliation.__unicode__(), u'Jeffery Horsburgh (Utah State University) - serious.email@usu.edu')


class TestActionBy(TestCase):
    @staticmethod
    def create_action_by():
        affiliation = TestAffiliation.create_usu_affiliation()
        action = TestAction.create_visit_action()
        action_by = ActionBy(**models_data['usu_visit_action_by'])
        action_by.affiliation = affiliation
        action_by.action = action
        return action_by

    def setUp(self):
        self.action_by = self.create_action_by()

    def test_string_representation(self):
        self.assertEqual(str(self.action_by), 'Site Visit - 1991-08-17 1:20 -7: Jeffery Horsburgh (Utah State University) - serious.email@usu.edu')
        self.assertEqual(self.action_by.__unicode__(), u'Site Visit - 1991-08-17 1:20 -7: Jeffery Horsburgh (Utah State University) - serious.email@usu.edu')


class TestMethod(TestCase):
    @staticmethod
    def create_deployment_method():
        method_type = MethodType(**models_data['deployment_method_type'])
        method = Method(**models_data['deployment_method'])
        method.method_type = method_type
        return method

    @staticmethod
    def create_visit_method():
        method_type = MethodType(**models_data['visit_method_type'])
        method = Method(**models_data['visit_method'])
        method.method_type = method_type
        return method

    def setUp(self):
        self.method = self.create_deployment_method()

    def test_string_representation(self):
        self.assertEqual(str(self.method), 'Instrument deployment: Deployment')
        self.assertEqual(self.method.__unicode__(), u'Instrument deployment: Deployment')


class TestProcessingLevel(TestCase):
    @staticmethod
    def create_raw_processing_level():
        processing_level = ProcessingLevel(**models_data['raw_processing_level'])
        return processing_level

    def setUp(self):
        self.processing_level = self.create_raw_processing_level()

    def test_string_representation(self):
        self.assertEqual(str(self.processing_level), 'Raw (Raw and Unprocessed Data)')
        self.assertEqual(self.processing_level.__unicode__(), u'Raw (Raw and Unprocessed Data)')


class TestUnit(TestCase):
    @staticmethod
    def create_degree_celsius_unit():
        unit_type = UnitType(**models_data['temperature_unit_type'])
        unit = Unit(**models_data['degrees_celsius_unit'])
        unit.unit_type = unit_type
        return unit

    @staticmethod
    def create_feet_distance_unit():
        unit_type = UnitType(**models_data['length_unit_type'])
        unit = Unit(**models_data['coordinate_location_unit'])
        unit.unit_type = unit_type
        return unit

    @staticmethod
    def create_time_spacing_unit():
        unit_type = UnitType(**models_data['time_unit_type'])
        unit = Unit(**models_data['time_spacing_unit'])
        unit.unit_type = unit_type
        return unit

    def setUp(self):
        self.unit = self.create_degree_celsius_unit()

    def test_string_representation(self):
        self.assertEqual(str(self.unit), 'Temperature: degC (degree celsius)')
        self.assertEqual(self.unit.__unicode__(), u'Temperature: degC (degree celsius)')


class TestVariable(TestCase):
    @staticmethod
    def create_air_temperature_variable():
        variable_type = VariableType(**models_data['climate_variable_type'])
        variable_name = VariableName(**models_data['temperature_variable_name'])
        variable = Variable(**models_data['avg_air_temperature_variable'])
        variable.variable_type = variable_type
        variable.variable_name = variable_name
        return variable

    def setUp(self):
        self.variable = self.create_air_temperature_variable()

    def test_string_representation(self):
        self.assertEqual(str(self.variable), 'Temperature: AirTemp_Avg (Climate)')
        self.assertEqual(self.variable.__unicode__(), u'Temperature: AirTemp_Avg (Climate)')


class TestResult(TestCase):
    @staticmethod
    def create_air_temperature_coverage_result():
        feature_action = TestFeatureAction.create_site_visit_feature_action()
        result_type = ResultType(**models_data['series_coverage_result_type'])
        variable = TestVariable.create_air_temperature_variable()
        unit = TestUnit.create_degree_celsius_unit()
        processing_level = TestProcessingLevel.create_raw_processing_level()
        status = Status(**models_data['ongoing_result_status'])
        sampled_medium = Medium(**models_data['air_medium'])

        result = Result(**models_data['air_temperature_coverage_result'])
        result.feature_action = feature_action
        result.result_type = result_type
        result.variable = variable
        result.unit = unit
        result.processing_level = processing_level
        result.status = status
        result.sampled_medium = sampled_medium

        return result

    def setUp(self):
        self.result = self.create_air_temperature_coverage_result()

    def test_string_representation(self):
        self.assertEqual(str(self.result), '2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC')
        self.assertEqual(self.result.__unicode__(), u'2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC')


class TestTimeSeriesResult(TestCase):
    @staticmethod
    def create_air_temperature_time_series_result():
        intended_time_spacing_unit = TestUnit.create_time_spacing_unit()
        aggregation_statistic_cv = AggregationStatistic(**models_data['continuous_aggregation_statistic'])
        x_location_unit = TestUnit.create_feet_distance_unit()
        y_location_unit = TestUnit.create_feet_distance_unit()
        z_location_unit = TestUnit.create_feet_distance_unit()
        result = TestResult.create_air_temperature_coverage_result()

        time_series_result = TimeSeriesResult(**models_data['air_temperature_time_series_result'])
        time_series_result.intended_time_spacing_unit = intended_time_spacing_unit
        time_series_result.aggregation_statistic_cv = aggregation_statistic_cv
        time_series_result.x_location_unit = x_location_unit
        time_series_result.y_location_unit = y_location_unit
        time_series_result.z_location_unit = z_location_unit
        time_series_result.result = result

        return time_series_result

    def setUp(self):
        self.time_series_result = self.create_air_temperature_time_series_result()

    def test_string_representation(self):
        self.assertEqual(str(self.time_series_result), '2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC')
        self.assertEqual(self.time_series_result.__unicode__(), u'2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC')


class TestTimeSeriesResultValue(TestCase):
    @staticmethod
    def create_air_temperature_time_series_value():
        result = TestTimeSeriesResult.create_air_temperature_time_series_result()
        censor_code = CensorCode(**models_data['non_detect_censor_code'])
        quality_code = QualityCode(**models_data['good_quality_code'])
        time_aggregation_interval_unit = TestUnit.create_time_spacing_unit()

        series_value = TimeSeriesResultValue(**models_data['air_temperature_result_value'])
        series_value.result = result
        series_value.censor_code = censor_code
        series_value.quality_code = quality_code
        series_value.time_aggregation_interval_unit = time_aggregation_interval_unit

        return series_value

    def setUp(self):
        self.time_series_value = self.create_air_temperature_time_series_value()

    def test_string_representation(self):
        self.assertEqual(str(self.time_series_value), '1.5 at 2016-05-23 6:33 (2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC)')
        self.assertEqual(self.time_series_value.__unicode__(), u'1.5 at 2016-05-23 6:33 (2016-04-20 2:10 - Time series coverage (Temperature): AirTemp_Avg degC)')
