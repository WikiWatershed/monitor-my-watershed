from collections import namedtuple
import copy
import datetime
from typing import Dict, Any, Iterable, Tuple, Union, List
import math
import uuid

import sqlalchemy
from django.conf import settings

from odm2 import odm2datamodels
from odm2.exceptions import ObjectNotFound
from streamwatch import timeutils
from utils.s3_uploader import S3Interface

odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models

STREAMWATCH_METHOD_ID = 1
CENSOR_CODE_CV_NONDETECT = "Non-detect"
NONDETECT_FIELD_SUFFIX = "_nondetect"


def variable_choice_options(
    variable_domain_cv: str, include_blank: bool = True
) -> Iterable[Tuple]:
    """Get categorical options from the variables table of the ODM2 database"""
    query = (
        sqlalchemy.select(
            odm2_models.Variables.variableid, odm2_models.Variables.variabledefinition
        )
        .where(odm2_models.Variables.variabletypecv == variable_domain_cv)
        .order_by(odm2_models.Variables.variableid)
    )
    records = odm2_engine.read_query(query, output_format="records").tolist()
    if include_blank:
        records = [(None, "")] + records
    return records


def sampling_feature_code_to_id(code: str) -> Union[int, None]:
    """Take a sampling_feature_code and finds the corresponding sampling_feature_id"""
    query = sqlalchemy.select(odm2_models.SamplingFeatures).where(
        odm2_models.SamplingFeatures.samplingfeaturecode == code
    )
    result = odm2_engine.read_query(query, output_format="dict")
    if result:
        return result[0]["samplingfeatureid"]
    return None


def samplingfeature_assessments(sampling_feature_code: str) -> Dict[str, Any]:
    """Get a joined list joined the featureactions and actions based on sampling_feature_code"""
    sampling_feature_id = sampling_feature_code_to_id(sampling_feature_code)
    if sampling_feature_id is None:
        return {}

    query = (
        sqlalchemy.select(odm2_models.FeatureActions, odm2_models.Actions)
        .join(
            odm2_models.Actions,
            odm2_models.FeatureActions.actionid == odm2_models.Actions.actionid,
        )
        .where(odm2_models.FeatureActions.samplingfeatureid == sampling_feature_id)
        .where(odm2_models.Actions.methodid == 1)
        # .order_by(odm2_models.Actions.begindatetime)
    )
    results = odm2_engine.read_query(query, output_format="dict")

    # acquire additional data
    for result in results:
        # convert UTC time to local time
        result["begindatetime"] = result["begindatetime"] - datetime.timedelta(
            hours=result["begindatetimeutcoffset"]
        )
        adapter = StreamWatchODM2Adapter.from_action_id(result["actionid"])
        result["adapter_attributes"] = adapter.to_dict(string_format=True)
        result["adapter"] = adapter

    return results


def delete_streamwatch_assessment(action_id: int) -> None:
    """Deletes a StreamWatch assessment from the database based on the parent action id"""
    odm2_engine.delete_object(odm2_models.Actions, action_id)


def get_odm2_units() -> Dict[int, Dict[str, Any]]:
    """Get a dictionary of units in the ODM2 data"""
    query = sqlalchemy.select(odm2_models.Units)
    df = odm2_engine.read_query(query, output_format="dataframe")
    df = df.set_index("unitsid")
    return df.to_dict(orient="index")


def get_odm2_variables() -> Dict[int, Dict[str, Any]]:
    """Get a dictionary of variables in the ODM2 data"""
    query = sqlalchemy.select(odm2_models.Variables)
    df = odm2_engine.read_query(query, output_format="dataframe")
    df = df.set_index("variableid")
    return df.to_dict(orient="index")


def affiliation_to_person(afflication_id: int) -> str:
    """Returns the person name and organization for a given afflication"""
    affiliation = odm2_engine.read_object(odm2_models.Affiliations, afflication_id)
    try:
        organization = odm2_engine.read_object(
            odm2_models.Organizations, affiliation["organizationid"]
        )
        org_name = organization["organizationname"]
    except ObjectNotFound:
        org_name = None
    account = odm2_engine.read_object(odm2_models.Accounts, affiliation["accountid"])
    return f"{account['accountfirstname']} {account['accountlastname']} {f'({org_name})' if org_name else ''}"


def get_assessment_summary_information(sampling_feature_code: str) -> dict[str, Any]:
    """Returns StreamWatch assessment information for a given sampling feature code"""
    ASSESSMENT_TYPES = ["school", "chemical", "biological", "bacterial"]

    summary = {t: 0 for t in ASSESSMENT_TYPES}
    summary["most_recent"] = None

    sampling_feature_id = sampling_feature_code_to_id(sampling_feature_code)
    query = (
        sqlalchemy.select(odm2_models.Actions)
        .join(
            odm2_models.FeatureActions,
            odm2_models.FeatureActions.actionid == odm2_models.Actions.actionid,
        )
        .where(odm2_models.FeatureActions.samplingfeatureid == sampling_feature_id)
        .where(odm2_models.Actions.methodid == STREAMWATCH_METHOD_ID)
        .order_by(sqlalchemy.desc(odm2_models.Actions.begindatetime))
    )
    assessments = odm2_engine.read_query(query, output_format="dict", orient="records")

    if not assessments:
        return summary
    assessment_datetime = assessments[0]["begindatetime"] + datetime.timedelta(
        hours=assessments[0]["begindatetimeutcoffset"]
    )
    summary["most_recent"] = assessment_datetime
    for assessment in assessments:
        for assessment_type in ASSESSMENT_TYPES:
            if assessment_type in str(assessment["actiondescription"]):
                summary[assessment_type] += 1
    return summary


__FIELDS = ("variable_identifier", "adapter_class", "units", "medium", "taxonomic")
FieldConfig = namedtuple(
    "FieldConfig", field_names=__FIELDS, defaults=(None,) * len(__FIELDS)
)


class CATParameter:
    def __init__(
        self, parameter: str = None, measurement: float = None, unit: int = None
    ) -> None:
        self.parameter = parameter
        self.measurement = measurement
        self.unit = unit


class CATMeasurement:
    def __init__(
        self, name: str = None, id: str = None, cal_date: datetime = None
    ) -> None:
        self.name = name
        self.id = id
        self.cal_date = cal_date


class _BaseFieldAdapter:
    QUALITY_CODE_CV = "None"
    PROCESSING_LEVEL = 1  # Indicating raw results.
    VALUE_FIELD_NAME = ""  # The database field to return from read method, subclasses should implement this as class attribute.

    @classmethod
    def create_result(
        cls,
        feature_action_id: int,
        config: FieldConfig,
        result_type: str,
        variable_id: int = None,
        datetime: datetime.datetime = None,
        utc_offset: int = None,
    ) -> int:
        """Create a ODM2 result record"""
        result = odm2_models.Results()
        result.featureactionid = feature_action_id
        result.resulttypecv = result_type
        result.variableid = variable_id if variable_id else config.variable_identifier
        result.taxonomicclassifierid = config.taxonomic
        result.unitsid = config.units
        result.processinglevelid = cls.PROCESSING_LEVEL
        result.resultdatetime = datetime
        result.resultdatetimeutcoffset = utc_offset
        result.sampledmediumcv = config.medium
        result.valuecount = -9999
        return odm2_engine.create_object(result)

    @classmethod
    def read(cls, database_record: Dict[str, Any]) -> Any:
        return database_record[cls.VALUE_FIELD_NAME]

    @classmethod
    def get_result_records(
        cls,
        feature_action_id: int,
        variable_id: int = None,
        variable_type_cv: str = None,
        taxonomic_classifier: int = None,
    ) -> List[Dict[str, Any]]:
        query = (
            sqlalchemy.select(odm2_models.Results)
            .join(
                odm2_models.FeatureActions,
                odm2_models.FeatureActions.featureactionid
                == odm2_models.Results.featureactionid,
            )
            .join(
                odm2_models.Variables,
                odm2_models.Variables.variableid == odm2_models.Results.variableid,
            )
            .where(odm2_models.FeatureActions.featureactionid == feature_action_id)
            .where(odm2_models.Results.taxonomicclassifierid == taxonomic_classifier)
        )
        if variable_id:
            query = query.where(odm2_models.Results.variableid == variable_id)
        if variable_type_cv:
            query = query.where(
                odm2_models.Variables.variabletypecv == variable_type_cv
            )
        results = odm2_engine.read_query(query, output_format="dict")

        if not results:
            raise KeyError(
                f"No result records for feature_action_id:{feature_action_id}"
            )
        return results


"http://vocabulary.odm2.org/variablename/taxaCount/"


class _ChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating single select field data into ODM2 results structure

    Implemented through the `results` table. Presence of a result record means a field
    was populated, and the `variableid` of the result record indicates the categorical value
    that was selected.
    """

    RESULT_TYPE_CV = "Category observation"
    VALUE_FIELD_NAME = "variableid"

    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        result_id = cls.create_result(
            feature_action_id, config, cls.RESULT_TYPE_CV, value
        )

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        result_records = cls.get_result_records(
            feature_action_id, variable_type_cv=config.variable_identifier
        )
        if not result_records:
            raise KeyError(
                f"No result records for feature_action_id:{feature_action_id} and variableid:{config.variable_identifier}"
            )
        result_id = result_records[0]["resultid"]
        if not value and result_records:
            odm2_engine.delete_object(odm2_models.Results, result_id)
            return
        odm2_engine.update_object(odm2_models.Results, result_id, {"variableid": value})


class _MultiChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating multi-select field into ODM2 results structure

    Implemented through the `results` table. Presence of a result record means an
    option was selected and the `variableid` of the result record indicates which
    categorical value was selected. As a multi-choice field, when two or more
    options are selected, each selected value will be stored in the database
    as distinct result record. Creating a full list of which options were selected
    requires reading the `variableid` from all result records with the same
    `variabletypecv` field.
    """

    RESULT_TYPE_CV = "Category observation"
    VALUE_FIELD_NAME = "variableid"

    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        if not isinstance(value, list):
            value = [value]
        for selected in value:
            cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV, selected)

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        result_records = cls.get_result_records(
            feature_action_id, variable_type_cv=config.variable_identifier
        )
        if not result_records:
            raise KeyError(
                f"No result records for feature_action_id:{feature_action_id} and variableid:{config.variable_identifier}"
            )

        saved_results = {r["variableid"]: r["resultid"] for r in result_records}

        if not isinstance(value, list) and value:
            value = [value]
        for selected in value:
            if int(selected) in saved_results:
                saved_results.pop(int(selected))
            elif int(selected) not in saved_results:
                cls.create_result(
                    feature_action_id, config, cls.RESULT_TYPE_CV, selected
                )

        if saved_results:
            for resultid in saved_results.values():
                odm2_engine.delete_object(odm2_models.Results, resultid)


class _FloatFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating float value into ODM2 results structure

    Implemented through the `MeasurementResults` and `MeasurementResultValues` tables.
    """

    RESULT_TYPE_CV = "Measurement"
    CENSOR_CODE_CV = "Unknown"
    AGGREGATION_STATISTIC_CV = "Sporadic"
    TIME_AGGREGATION_INTERVAL = 1.0
    TIME_AGGREGATION_INTERVAL_UNIT_ID = 2  # hour minute
    VALUE_FIELD_NAME = "measurement_datavalue"

    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV)

        cls.create_measurement_result(result_id)
        cls.create_measurement_result_value(result_id, value, datetime, utc_offset)

    @classmethod
    def create_measurement_result(
        cls, result_id: int, censor_code: str = CENSOR_CODE_CV
    ) -> None:
        measurementresult = odm2_models.MeasurementResults()
        measurementresult.resultid = result_id
        measurementresult.censorcodecv = censor_code
        measurementresult.qualitycodecv = cls.QUALITY_CODE_CV
        measurementresult.aggregationstatisticcv = cls.AGGREGATION_STATISTIC_CV
        measurementresult.timeaggregationinterval = cls.TIME_AGGREGATION_INTERVAL
        measurementresult.timeaggregationintervalunitsid = (
            cls.TIME_AGGREGATION_INTERVAL_UNIT_ID
        )
        odm2_engine.create_object(measurementresult, preserve_pkey=True)

    @classmethod
    def create_measurement_result_value(
        cls, result_id: int, value: float, datetime: datetime, utc_offset: int
    ) -> None:
        measurementresultvalue = odm2_models.MeasurementResultValues()
        measurementresultvalue.resultid = result_id
        measurementresultvalue.datavalue = value
        measurementresultvalue.valuedatetime = datetime
        measurementresultvalue.valuedatetimeutcoffset = utc_offset
        odm2_engine.create_object(measurementresultvalue)

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        result_records = cls.get_result_records(
            feature_action_id,
            variable_id=config.variable_identifier,
            taxonomic_classifier=config.taxonomic_classifier,
        )
        # main update loop
        # Definitions
        #   Form: refers to the value provided by user from frontend
        #   Record: refers to MeasurementResultValue database record associated with result_id
        #   Result : refers to odm2.Result database record
        # Explanation of possible states
        #   1. Form = None
        #       delete result and child records
        #   2. Form = Float | Record -> Record != Exists -->
        #       check if MeasureResults record exists --> false = create record
        #       create MeasurementResultValues record
        #   3. From is float | Record is Float | Record != Form -->

        # Guard clause for result record does not exist
        # This should not be necessary and should be checked higher up in the
        # processing steps
        # TODO test if this can be removed
        if not result_records:
            raise KeyError(
                f"No result records for feature_action_id:{feature_action_id} and variableid:{config.variable_identifier}"
            )

        # get the result database record for this form field
        result = result_records[0]
        result_id = result["resultid"]

        # Address state 1
        if not value:
            odm2_engine.delete_object(odm2_models.Results, result_id)
            return

        try:
            # Address state 3. If record does not exist catch exception and move to state 2
            query = sqlalchemy.select(odm2_models.MeasurementResultValues).where(
                odm2_models.MeasurementResultValues.resultid == result_id
            )
            measurement_result_value = odm2_engine.read_query(
                query, output_format="dict"
            )
            value_id = measurement_result_value[0]["valueid"]
            odm2_engine.update_object(
                odm2_models.MeasurementResultValues, value_id, {"datavalue": value}
            )
            # if the record does not exist there will be an index error
        except IndexError:
            # state 2. We need to create a new MeasureResultValues record.

            # datetime and utc_offset are required for MeasurementResultValue record.
            # ideally that information can be pulled from the result records, but there are
            # legacy records that might not have that information populated, so fall back to the
            # server time as a backup/default.
            date = (
                result["resultdatetime"]
                if result["resultdatetime"]
                else datetime.datetime.now()
            )
            utc_offset = (
                result["resultdatetimeutcoffset"]
                if result["resultdatetimeutcoffset"]
                else 0
            )

            # check if there is still existing MeasureResults record
            query = sqlalchemy.select(odm2_models.MeasurementResults).where(
                odm2_models.MeasurementResults.resultid == result_id
            )
            measurement_result = odm2_engine.read_query(query, output_format="dict")
            if len(measurement_result) == 0:
                cls.create_measurement_result(result_id=result_id)

            # creating missing MeasurementResultValue record
            cls.create_measurement_result_value(
                result_id=result_id,
                value=value,
                datetime=date,
                utc_offset=utc_offset,
            )

        # update censorcode_cv to ensure Non-detected does not persist
        odm2_engine.update_object(
            odm2_models.MeasurementResults,
            result_id,
            {"censorcodecv": cls.CENSOR_CODE_CV},
        )


class _FloatFieldNondetectAdapter(_FloatFieldAdapter):
    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        result_id = cls.create_result(
            feature_action_id,
            config,
            cls.RESULT_TYPE_CV,
        )

        # if non-detect was selected, form clean data method should return value=True
        # and we should override default behavior and mark record with a special censor
        # code indicating non-detected. Otherwise we want the default behavior.
        censor_code = (
            CENSOR_CODE_CV_NONDETECT if value is True else super().CENSOR_CODE_CV
        )

        cls.create_measurement_result(result_id, censor_code)
        if value is not True:
            cls.create_measurement_result_value(result_id, value, datetime, utc_offset)

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        """Updates database to reflect state of form (value)"""
        ### main update loop
        # We use boolean=True to indicate a non-detect, other value should be a float
        # Definitions
        #   Form: refers to the value provided by user from frontend
        #   Record: refers to MeasurementResultValue database record associated with result_id
        #   Result : refers to odm2.Result database record
        # Explanation of possible states
        #   1. Form = Float | Record -> Record != Exists -->
        #       Use super class (FloatFieldAdapter)
        #   2. From is float | Record if Float | Record != Form -->
        #       Use super class (FloatFieldAdapter)
        #   3. Form = True(non-detect) | Record = Exists -->
        #       Delete MeasurementResultValues Record
        #       Update CENSOR_CODE of MeasurementResults record
        #   4. Form = True(non-detect) | Record = Does Not Exists -->
        #       Update CENSOR_CODE of MeasurementResults record
        #   5. Form = None -->
        #       Use super class (FloatFieldAdapter)

        # if the value is float (not True) then we can use the super class method to handle this
        if value is not True or value is None:
            return super().update(value, feature_action_id, config)

        # fetch result information from the database
        result_records = cls.get_result_records(
            feature_action_id, config.variable_identifier
        )
        result_id = result_records[0]["resultid"]

        try:
            # State 3
            query = sqlalchemy.select(odm2_models.MeasurementResultValues).where(
                odm2_models.MeasurementResultValues.resultid == result_id
            )
            measurement_result_value = odm2_engine.read_query(
                query, output_format="dict"
            )
            value_id = measurement_result_value[0]["valueid"]
            odm2_engine.delete_object(odm2_models.MeasurementResultValues, value_id)
        except IndexError:
            # indicates state 4. If the MeasurementResultValue did not exist
            # then we should be able to just proceed with setting the cencorcode_cv
            # to indicate that the measurement is a non-detect
            pass
        finally:
            odm2_engine.update_object(
                odm2_models.MeasurementResults,
                result_id,
                {"censorcodecv": CENSOR_CODE_CV_NONDETECT},
            )

    @classmethod
    def read(cls, database_record: Dict[str, Any]) -> Any:
        if database_record["measurement_censorcodecv"] == CENSOR_CODE_CV_NONDETECT:
            return True
        return database_record[cls.VALUE_FIELD_NAME]


class _TextFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating string value into ODM2 results structure

    Implemented through the `CategoricalResults` and `CategoricalResultValues` tables.
    """

    RESULT_TYPE_CV = "Category observation"
    VALUE_FIELD_NAME = "categorical_datavalue"

    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV)

        categoricalresult = odm2_models.CategoricalResults()
        categoricalresult.resultid = result_id
        categoricalresult.qualitycodecv = cls.QUALITY_CODE_CV
        odm2_engine.create_object(categoricalresult, preserve_pkey=True)

        categoricalresultvalue = odm2_models.CategoricalResultValues()
        categoricalresultvalue.resultid = result_id
        categoricalresultvalue.datavalue = value
        categoricalresultvalue.valuedatetime = datetime
        categoricalresultvalue.valuedatetimeutcoffset = utc_offset
        odm2_engine.create_object(categoricalresultvalue)

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        result_records = cls.get_result_records(
            feature_action_id,
            variable_id=config.variable_identifier,
            taxonomic_classifier=config.taxonomic,
        )
        if not result_records:
            raise KeyError(
                f"No result records for feature_action_id:{feature_action_id} and variableid:{config.variable_identifier}"
            )
        if len(result_records) > 1:
            raise ValueError(
                f"Multiple result records returned (found {len(result_records)}). Executing update runs risk of updating incorrect data field"
            )
        result_id = result_records[0]["resultid"]

        if not value:
            odm2_engine.delete_object(odm2_models.Results, result_id)
            return

        # TODO: we should implemented an update_query method in ODM2Engine
        query = sqlalchemy.select(odm2_models.CategoricalResultValues).where(
            odm2_models.CategoricalResultValues.resultid == result_id
        )
        categorical_result_value = odm2_engine.read_query(query, output_format="dict")
        value_id = categorical_result_value[0]["valueid"]
        odm2_engine.update_object(
            odm2_models.CategoricalResultValues, value_id, {"datavalue": value}
        )


class _ObjectFieldAdapter(_BaseFieldAdapter):
    RESULT_TYPE_CV = "Object store"
    VALUE_FIELD_NAME = "objectstore_objecturi"
    CENSOR_CODE_CV = "Unknown"
    BUCKET = settings.SITE_PHOTOS_S3_BUCKET

    @classmethod
    def create(
        cls,
        value: Any,
        datetime: datetime.datetime,
        utc_offset: int,
        feature_action_id: int,
        config: FieldConfig,
    ) -> None:
        if not value:
            return
        # upload the file to S3
        interface = S3Interface()
        obj_id = cls.__upload_to_s3(interface, value)

        result_id = cls.create_result(
            feature_action_id,
            config,
            cls.RESULT_TYPE_CV,
            variable_id=config.variable_identifier,
        )

        result = odm2_models.ObjectStoreResults()
        result.resultid = result_id
        result.qualitycodecv = cls.QUALITY_CODE_CV
        result.censorcodecv = cls.CENSOR_CODE_CV
        result.objecttype = value.content_type
        odm2_engine.create_object(result, preserve_pkey=True)

        resultvalue = odm2_models.ObjectStoreResultValues()
        resultvalue.resultid = result_id
        resultvalue.objecturi = obj_id
        resultvalue.datavalue = value
        resultvalue.valuedatetime = datetime
        resultvalue.valuedatetimeutcoffset = utc_offset
        odm2_engine.create_object(resultvalue)

        return None

    @classmethod
    def update(cls, value: Any, feature_action_id: int, config: FieldConfig) -> None:
        result_records = cls.get_result_records(
            feature_action_id,
            variable_id=config.variable_identifier,
            taxonomic_classifier=config.taxonomic,
        )
        result_id = result_records[0]["resultid"]

        query = sqlalchemy.select(odm2_models.ObjectStoreResultValues).where(
            odm2_models.ObjectStoreResultValues.resultid == result_id
        )
        object_store_result_value = odm2_engine.read_query(query, output_format="dict")
        value_id = object_store_result_value[0]["valueid"]

        interface = S3Interface()
        # we want to get existing photo uuid so we can delete the object in s3
        # we don't want to orphan images or pay to host images that have no database
        # record assoicated with them
        existing_obj_uuid = object_store_result_value[0]["objecturi"]
        cls.__delete_from_s3(interface, existing_obj_uuid)

        # delete use case, form class will code values as 'delete'
        if value == "delete":
            odm2_engine.delete_object(odm2_models.ObjectStoreResultValues, value_id)
            odm2_engine.delete_object(odm2_models.ObjectStoreResults, result_id)
            odm2_engine.delete_object(odm2_models.Results, result_id)
            return

        # general update case, user provided new image
        # upload the new image
        obj_id = ""
        if value != "":
            obj_id = cls.__upload_to_s3(interface, value)
        odm2_engine.update_object(
            odm2_models.ObjectStoreResultValues, value_id, {"objecturi": obj_id}
        )

    @classmethod
    def get_uri(cls, key: str) -> str:
        """Given a S3 key, formulates and return uri to access object"""
        region = settings.COGNITO_REGION
        bucket = settings.SITE_PHOTOS_S3_BUCKET
        uri = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return uri

    @classmethod
    def read(cls, database_record: Dict[str, Any]) -> Any:
        uri = super().read(database_record)
        return cls.get_uri(uri)

    @classmethod
    def __upload_to_s3(
        cls,
        interface: S3Interface,
        obj: Any,
    ) -> str:
        obj_id = str(uuid.uuid4())
        interface.put_object(
            key=obj_id,
            obj=obj.file,
            content_type=obj.content_type,
            bucket=cls.BUCKET,
        )
        return obj_id

    @classmethod
    def __delete_from_s3(
        cls,
        interface: S3Interface,
        uuid: str,
    ):
        interface.delete_object(key=uuid, bucket=cls.BUCKET)


class StreamWatchODM2Adapter:
    """Adapter class for translating streamwatch form data in and out of ODM2"""

    ROOT_METHOD_ID = STREAMWATCH_METHOD_ID
    PARENT_ACTION_TYPE_CV = "Field activity"
    VARIABLE_CODE = "variableid"
    VARIABLE_TYPE = "variabletypecv"
    TAXONOMIC_ID = "taxonomicclassifierid"

    # This is intended be more flexible way to map form field ODM2 data
    # and limit the hardcoding to a single location
    # FieldConfig(variable_identifier:str|int, adapterclass|Class, units:int, medium:str, taxonomicid:optional[int])
    # for variable_identifier int corresponding to variableid should be populated for Text and Floats
    #   ans str corresponding to variabletypecv should be populated for Choice and MultiChoice
    # fmt: off
    PARAMETER_CROSSWALK = {
        "algae_amount": FieldConfig( "algaeAmount", _ChoiceFieldAdapter, 394, "Liquid aqueous"),
        "algae_type": FieldConfig( "algaeType", _MultiChoiceFieldAdapter, 394, "Liquid aqueous"),
        "aquatic_veg_amount": FieldConfig( "aquaticVegetation", _ChoiceFieldAdapter, 394, "Liquid aqueous"),
        "aquatic_veg_type": FieldConfig( "aquaticVegetationType", _MultiChoiceFieldAdapter, 394, "Liquid aqueous"),
        "site_observation": FieldConfig(540, _TextFieldAdapter, 394, "Not applicable"),
        "simple_air_temperature": FieldConfig(541, _FloatFieldAdapter, 362, "Air"),
        "simple_dissolved_oxygen": FieldConfig( 544, _FloatFieldNondetectAdapter, 404, "Liquid aqueous"),
        "simple_nitrate": FieldConfig( 546, _FloatFieldNondetectAdapter, 404, "Liquid aqueous"),
        "simple_phosphate": FieldConfig( 547, _FloatFieldNondetectAdapter, 404, "Liquid aqueous"),
        "simple_ph": FieldConfig(543, _FloatFieldAdapter, 385, "Liquid aqueous"),
        "simple_salinity": FieldConfig( 545, _FloatFieldNondetectAdapter, 428, "Liquid aqueous"),
        "simple_turbidity": FieldConfig( 550, _FloatFieldNondetectAdapter, 364, "Liquid aqueous"),
        "simple_water_temperature": FieldConfig( 542, _FloatFieldAdapter, 362, "Liquid aqueous"),
        "simple_woody_debris_amt": FieldConfig( "woodyDebris", _ChoiceFieldAdapter, 394, "Other"),
        "simple_woody_debris_type": FieldConfig( "woodyDebrisType", _ChoiceFieldAdapter, 394, "Other"),
        "simple_tree_canopy": FieldConfig( "treeCanopy", _ChoiceFieldAdapter, 394, "Other"),
        "simple_land_use": FieldConfig( "landUse", _MultiChoiceFieldAdapter, 394, "Other"),
        "surface_coating": FieldConfig( "surfaceCoating", _MultiChoiceFieldAdapter, 394, "Liquid aqueous"),
        "time_since_last_precip": FieldConfig( "precipitation", _ChoiceFieldAdapter, 394, "Other"),
        "clarity": FieldConfig("clarity", _ChoiceFieldAdapter, 394, "Liquid aqueous"),
        "water_color": FieldConfig( "waterColor", _ChoiceFieldAdapter, 394, "Liquid aqueous"),
        "water_movement": FieldConfig( "waterMovement", _ChoiceFieldAdapter, 394, "Liquid aqueous"),
        "water_odor": FieldConfig( "waterOdor", _MultiChoiceFieldAdapter, 394, "Liquid aqueous"),
        "water_odor_other": FieldConfig(585, _TextFieldAdapter, 394, "Liquid aqueous"),
        "weather_cond": FieldConfig("weather", _MultiChoiceFieldAdapter, 394, "Air"),
        "siteimage1": FieldConfig(3, _ObjectFieldAdapter, 394, "Not applicable"),
        "siteimage2": FieldConfig(4, _ObjectFieldAdapter, 394, "Not applicable"),
        "siteimage3": FieldConfig(5, _ObjectFieldAdapter, 394, "Not applicable"),
        "siteimage4": FieldConfig(6, _ObjectFieldAdapter, 394, "Not applicable"),
        "macro_ephemeroptera": FieldConfig(8, _FloatFieldAdapter, 394, "Organism", 2),
        "macro_plecoptera": FieldConfig(8, _FloatFieldAdapter, 394, "Organism", 1),
        "macro_hydropsychidae": FieldConfig(8, _FloatFieldAdapter, 394, "Organism", 16),
        "macro_other_caddisflies": FieldConfig( 8, _FloatFieldAdapter, 394, "Organism", 3),
        "macro_anisoptera": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 10),
        "macro_zygoptera": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 9),
        "macro_corydalidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 25),
        "macro_sialidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 26),
        "macro_coleoptera": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 27),
        "macro_athericidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 8),
        "macro_chironomidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 17),
        "macro_simuliidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 18),
        "macro_tipulidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 13),
        "macro_other_diptera": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 28),
        "macro_amphipoda": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 12),
        "macro_isopoda": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 11),
        "macro_decapoda": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 15),
        "macro_oligochaeta": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 22),
        "macro_hirudinea": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 20),
        "macro_turbellaria": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 19),
        "macro_gastropoda": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 29),
        "macro_sphaeriidae": FieldConfig(8, _FloatFieldAdapter, 409, "Organism", 30),
        "macro_comment": FieldConfig(7, _TextFieldAdapter, 394, "Other"),
    }
    # fmt: on

    def __init__(self, action_id: int) -> None:
        self.action_id = action_id
        self._attributes = {}

    def __reverse_crosswalk(cls) -> Dict[str, Any]:
        crosswalk = {}
        for k, v in cls.PARAMETER_CROSSWALK.items():
            variable, *_, taxonomic = v
            new_key = f"{variable}|{taxonomic}" if taxonomic else f"{variable}"
            crosswalk[new_key] = (k, *v[1:])
        return crosswalk

    @classmethod
    def from_action_id(cls, action_id: int) -> "StreamWatchODM2Adapter":
        """Constructor to retrieve existing form data from database based on assessment ActionId.

        input:
            action_id:int - the `actionid` corresponding to the root action for the StreamWatch assessment.

        output:
            StreamWatchODM2Adapter object
        """
        instance = cls(action_id)
        instance.__read_and_map_special_cases()
        data = instance.__read_from_database(action_id)
        instance.__map_database_to_dict(data)
        return instance

    @classmethod
    def from_dict(cls, form_data: Dict[str, Any]) -> "StreamWatchODM2Adapter":
        """Constructor to create new entry for a form on initial submittal

        inputs:
            form_data:Dict[str,Any] = a dictionary of data containing the form parameters
                with the dictionary key being the form field name, and the dictionary value
                being the user input value of the field from the form.

        output:
            StreamWatchODM2Adapter object
        """

        def create_parent_action(form_data: Dict[str, Any]) -> None:
            """Helper method to create a parent a new action StreamWatch parent action"""
            datetime_info = cls._get_datetime_and_utcoffset(form_data)

            action = odm2_models.Actions()
            action.actiontypecv = cls.PARENT_ACTION_TYPE_CV
            action.methodid = cls.ROOT_METHOD_ID
            action.begindatetime = datetime_info[0]
            action.begindatetimeutcoffset = datetime_info[1]
            # TODO - update if multiple assessment types is to be supported again
            # action.actiondescription = ",".join(form_data["assessment_type"])
            action.actiondescription = ",".join(["school"])

            action.actionid = odm2_engine.create_object(action)
            return action

        def create_investigator(
            action_id: int, afflication_id: int, is_lead=False
        ) -> None:
            actionby = odm2_models.ActionBy()
            actionby.actionid = action_id
            actionby.affiliationid = afflication_id
            actionby.isactionlead = is_lead
            odm2_engine.create_object(actionby)

        parent_action = create_parent_action(form_data)
        instance = StreamWatchODM2Adapter(parent_action.actionid)
        instance._attributes = form_data
        feature_action_id = instance._create_feature_action(
            instance.action_id, form_data["sampling_feature_id"]
        )
        create_investigator(instance.action_id, int(form_data["investigator1"]), True)
        if form_data["investigator2"] is not None:
            create_investigator(
                instance.action_id, int(form_data["investigator2"]), False
            )

        for key, value in form_data.items():
            # there a multiple siteimates but the crosswalk is designed as a 1:1 mapping
            # to get around this I added additional logic here to map any `siteimageXX` to `siteimage`
            if key not in instance.PARAMETER_CROSSWALK:
                continue
            config = instance.PARAMETER_CROSSWALK[key]

            # if non-detectable float, we need to check if additional non-detect field is checked and
            # override the value if bool is true.
            if config.adapter_class is _FloatFieldNondetectAdapter:
                value = True if form_data[f"{key}{NONDETECT_FIELD_SUFFIX}"] else value

            config.adapter_class.create(
                value,
                parent_action.begindatetime,
                parent_action.begindatetimeutcoffset,
                feature_action_id,
                config,
            )
        return instance

    @property
    def count_total_macros(self) -> int:
        count = 0
        for name, value in self._attributes.items():
            if "macro_" in name and "comment" not in name:
                count += value
        return count

    def __read_from_database(self, parent_action_id: int) -> List[Dict[str, Any]]:
        """Helper method to query the data from the database"""
        query = (
            sqlalchemy.select(
                odm2_models.Actions,
                odm2_models.FeatureActions,
                odm2_models.Results,
                odm2_models.Variables,
                odm2_models.MeasurementResults.censorcodecv.label(
                    "measurement_censorcodecv"
                ),
                odm2_models.MeasurementResultValues.datavalue.label(
                    "measurement_datavalue"
                ),
                odm2_models.CategoricalResultValues.datavalue.label(
                    "categorical_datavalue"
                ),
                odm2_models.ObjectStoreResultValues.objecturi.label(
                    "objectstore_objecturi"
                ),
            )
            .join(
                odm2_models.FeatureActions,
                odm2_models.FeatureActions.actionid == odm2_models.Actions.actionid,
            )
            .join(
                odm2_models.Results,
                odm2_models.Results.featureactionid
                == odm2_models.FeatureActions.featureactionid,
            )
            .join(
                odm2_models.Variables,
                odm2_models.Variables.variableid == odm2_models.Results.variableid,
            )
            .outerjoin(
                odm2_models.MeasurementResults,
                odm2_models.MeasurementResults.resultid == odm2_models.Results.resultid,
            )
            .outerjoin(
                odm2_models.MeasurementResultValues,
                odm2_models.MeasurementResultValues.resultid
                == odm2_models.MeasurementResults.resultid,
            )
            .outerjoin(
                odm2_models.CategoricalResults,
                odm2_models.CategoricalResults.resultid == odm2_models.Results.resultid,
            )
            .outerjoin(
                odm2_models.CategoricalResultValues,
                odm2_models.CategoricalResultValues.resultid
                == odm2_models.CategoricalResults.resultid,
            )
            .outerjoin(
                odm2_models.ObjectStoreResults,
                odm2_models.ObjectStoreResults.resultid == odm2_models.Results.resultid,
            )
            .outerjoin(
                odm2_models.ObjectStoreResultValues,
                odm2_models.ObjectStoreResultValues.resultid
                == odm2_models.ObjectStoreResults.resultid,
            )
            .where(
                odm2_models.Actions.actionid == parent_action_id
            )  # TODO: this eventually need to be scaled to include related actions
        )
        data = odm2_engine.read_query(query, output_format="dict")
        return data

    def __crosswalk_record(self, record: Dict[str, Any], config: FieldConfig) -> None:
        field = config[0]
        adapter = config[1]
        if adapter is _FloatFieldNondetectAdapter:
            value = adapter.read(record)
            field = f"{field}{NONDETECT_FIELD_SUFFIX}" if value is True else field
            self._attributes[field] = value
        # categorical/ single- or multi-choice
        if adapter in (
            _ChoiceFieldAdapter,
            _MultiChoiceFieldAdapter,
        ):
            if field not in self._attributes:
                self._attributes[field] = []
            self._attributes[field].append(adapter.read(record))
        else:
            self._attributes[field] = adapter.read(record)

    def __map_database_to_dict(self, data: Dict[str, Any]) -> None:
        """Reverses the database crosswalk to map data back to dictionary"""

        crosswalk = self.__reverse_crosswalk()
        for record in data:
            # TODO: The autompper models appear to incorrecty mappin taxonomicclassifierid to a float
            # this is a workaround until we replace those models with an explicit version
            if record[self.TAXONOMIC_ID] and not math.isnan(record[self.TAXONOMIC_ID]):
                record[self.TAXONOMIC_ID] = int(record[self.TAXONOMIC_ID])

            # different types of data fields are mapped to the databse differently.
            possible_keys = (
                # 1 record is coded with a variable code and taxonomic identifier
                f"{record[self.VARIABLE_CODE]}|{record[self.TAXONOMIC_ID]}",
                # 2 record is coded wth just a variable code
                f"{record[self.VARIABLE_CODE]}",
                # 3 record is coded wth a variable type (categorical parameters)
                f"{record[self.VARIABLE_TYPE]}",
            )

            for key in possible_keys:
                if key in crosswalk:
                    self.__crosswalk_record(record, crosswalk[key])
                    break

    def __read_and_map_special_cases(self) -> None:
        action = odm2_engine.read_object(odm2_models.Actions, self.action_id)
        self._attributes["assessment_type"] = []
        if action["actiondescription"]:
            self._attributes["assessment_type"] = action["actiondescription"].split(",")

        action_datetime_local = action["begindatetime"] - datetime.timedelta(
            hours=action["begindatetimeutcoffset"]
        )
        self._attributes["collect_date"] = action_datetime_local.date()
        self._attributes["collect_time"] = action_datetime_local.time()

        query = sqlalchemy.select(odm2_models.ActionBy).where(
            odm2_models.ActionBy.actionid == self.action_id
        )
        investigators = odm2_engine.read_query(query, output_format="dict")
        self._attributes["investigator1"] = None
        self._attributes["investigator2"] = None

        for investigator in investigators:
            if investigator["isactionlead"]:
                self._attributes["investigator1"] = investigator["affiliationid"]
                continue
            self._attributes["investigator2"] = investigator["affiliationid"]

    def _create_feature_action(self, actionid: int, sampling_feature_id: int) -> int:
        """Helper method to register an action to the SamplingFeature"""
        featureaction = odm2_models.FeatureActions.from_dict(
            {"samplingfeatureid": sampling_feature_id, "actionid": actionid}
        )
        return odm2_engine.create_object(featureaction)

    @classmethod
    def _get_datetime_and_utcoffset(
        cls, form_data: Dict[str, Any]
    ) -> Tuple[datetime.datetime, int]:
        """Helper function to format datatime and utcoffset based on form provided values"""
        date = form_data["collect_date"]
        time = form_data["collect_time"]
        timezone = form_data["collect_tz"]

        if date is None:
            date = datetime.datetime.now().date()
        if time is None:
            time = datetime.time(0, 0)
        utc_offset = timeutils.get_utcoffset(timezone)
        datetime_combined = datetime.datetime.combine(date, time)
        datetime_combined = datetime_combined + datetime.timedelta(hours=utc_offset[0])
        return datetime_combined, utc_offset[0]

    def to_dict(self, string_format: bool = False) -> Dict[str, Any]:
        """Return attributes as dictionary with form fields mapped as keys and user inputs as values

        inputs:
            string_format:boolean | optional | default=False
                Bool flag indicating if `variable` and `unit` parameters should be converted to strings

        outputs:
            Dict[str,Any]:
                Dictionary of form data with form field names mapped as keys and
                user inputs mapped to dictionary values.
        """
        if not string_format:
            return self._attributes

        data = copy.deepcopy(self._attributes)
        variables = get_odm2_variables()
        for key, value in self._attributes.items():
            # TODO we should really make this a multifield class
            if NONDETECT_FIELD_SUFFIX in key:
                key = key.removesuffix(NONDETECT_FIELD_SUFFIX)

            if key not in self.PARAMETER_CROSSWALK:
                continue
            config = self.PARAMETER_CROSSWALK[key]
            if (
                config.adapter_class is _ChoiceFieldAdapter
                or config.adapter_class is _MultiChoiceFieldAdapter
            ):
                data[key] = ", ".join(
                    [variables[x]["variabledefinition"] for x in value]
                )
            elif config.adapter_class is _FloatFieldNondetectAdapter:
                # if boolean indicating non-detect map to text
                if value is True:
                    data[key] = CENSOR_CODE_CV_NONDETECT

        if data["investigator1"]:
            data["investigator1"] = affiliation_to_person(data["investigator1"])
        if data["investigator2"]:
            data["investigator2"] = affiliation_to_person(data["investigator2"])

        if data["assessment_type"]:
            assessment_types = []
            for a_type in data["assessment_type"]:
                if a_type == "school":
                    assessment_types.append("StreamWatch Schools")
                elif a_type == "chemical":
                    assessment_types.append("Chemical Action Team")
                elif a_type == "biological":
                    assessment_types.append("Biological Action Team")
                elif a_type == "baterial":
                    assessment_types.append("Baterial Action Team")
            data["assessment_type"] = ", ".join(assessment_types)

        return data

    def update_from_dict(self, form_data: Dict[str, Any]) -> None:
        """Method to take dictionary of data from the form and update the database records

        inputs:
            Dict[str,Any]: Dictionary of form data with form field names mapped as keys and
                user inputs mapped to dictionary values.

        outputs:
            None
        """
        self._update_special_cases(form_data)

        parent_action = odm2_engine.read_object(odm2_models.Actions, self.action_id)
        query = sqlalchemy.select(odm2_models.FeatureActions).where(
            odm2_models.FeatureActions.actionid == parent_action["actionid"]
        )
        feature_action = odm2_engine.read_query(query, output_format="dict")
        feature_action_id = feature_action[0]["featureactionid"]
        for key, value in form_data.items():
            # if the field is not in the cross walk (e.g. a non-detect boolean field)
            if key not in self.PARAMETER_CROSSWALK:
                continue

            config = self.PARAMETER_CROSSWALK[key]
            # case where record does not yet exiusts (i.e. this is a new paramenter)
            if key not in self._attributes:
                config.adapter_class.create(
                    value,
                    parent_action["begindatetime"],
                    parent_action["begindatetimeutcoffset"],
                    feature_action_id,
                    config,
                )
            # special case for float non-detect where value update is in two fields
            elif config.adapter_class is _FloatFieldNondetectAdapter:
                # check if non-detect options checked
                check_box_value = form_data[f"{key}{NONDETECT_FIELD_SUFFIX}"]
                # if non-detect checked, override float field value
                value = check_box_value if check_box_value else value
                config.adapter_class.update(value, feature_action_id, config)
            # case where value has change
            elif value != self._attributes[key]:
                config.adapter_class.update(
                    value,
                    feature_action_id,
                    config,
                )

    def _update_special_cases(self, form_data: Dict[str, Any]) -> None:
        """Method to update form parameters that do not utilize a _BaseFieldAdapter subclass"""

        def get_actionby_bridgeid(
            action_id: int, lead: bool = True
        ) -> List[Dict[str, Any]]:
            query = (
                sqlalchemy.select(odm2_models.ActionBy.bridgeid)
                .where(odm2_models.ActionBy.actionid == action_id)
                .where(odm2_models.ActionBy.isactionlead == lead)
            )
            records = odm2_engine.read_query(query, output_format="dict")
            return records[0]["bridgeid"]

        def update_investigator(field_name: str, is_lead: bool) -> None:
            if form_data[field_name] and self._attributes[field_name]:
                bridge_id = get_actionby_bridgeid(self.action_id, is_lead)
                odm2_engine.update_object(
                    odm2_models.ActionBy,
                    bridge_id,
                    {"affiliationid": form_data[field_name]},
                )
            elif form_data[field_name] and not self._attributes[field_name]:
                action_by = odm2_models.ActionBy()
                action_by.actionid = self.action_id
                action_by.affiliationid = form_data[field_name]
                action_by.isactionlead = is_lead
                odm2_engine.create_object(action_by)
            elif not form_data[field_name] and self._attributes[field_name]:
                bridge_id = get_actionby_bridgeid(self.action_id, is_lead)
                odm2_engine.delete_object(odm2_models.ActionBy, bridge_id)

        if (
            form_data["collect_date"] != self._attributes["collect_date"]
            or form_data["collect_time"] != self._attributes["collect_time"]
        ):
            datetime_info = self._get_datetime_and_utcoffset(form_data)
            odm2_engine.update_object(
                odm2_models.Actions,
                self.action_id,
                {
                    "begindatetime": datetime_info[0],
                    "begindatetimeutcoffset": datetime_info[1],
                },
            )

        # site photos
        # we need to support multiple photo uploads which does not fit nicely into

        # Supports multiple assessments on single form. Feature was disabled at TWI request for the time being.
        # if form_data["assessment_type"] != self._attributes["assessment_type"]:
        #    odm2_engine.update_object(
        #        odm2_models.Actions,
        #        self.action_id,
        #        {"actiondescription": ",".join(form_data["assessment_type"])},
        #    )

        update_investigator("investigator1", True)
        update_investigator("investigator2", False)
