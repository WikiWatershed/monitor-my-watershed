from collections import namedtuple 
import datetime
from typing import Dict, Any, Iterable, Tuple, Union, List

import sqlalchemy

from odm2 import odm2datamodels


odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models


def variable_choice_options(variable_domain_cv:str) -> Iterable[Tuple]:
    """Get categorical options from the variables table of the ODM2 database"""
    query = (sqlalchemy.select(odm2_models.Variables.variableid, odm2_models.Variables.variabledefinition)
            .where(odm2_models.Variables.variabletypecv == variable_domain_cv)
        )
    records = odm2_engine.read_query(query, output_format='records')
    return records


def sampling_feature_code_to_id(code:str) -> Union[int,None]:
    """Take a sampling_feature_code and finds the corresponding sampling_feature_id"""
    query = (sqlalchemy.select(odm2_models.SamplingFeatures)
        .where(odm2_models.SamplingFeatures.samplingfeaturecode == code)
        )
    result = odm2_engine.read_query(query, output_format='dict')
    if result: return result[0]['samplingfeatureid']
    return None


def samplingfeature_assessments(sampling_feature_code:str) -> Dict[str,Any]:
    """Get a joined list joined the featureactions and actions based on sampling_feature_code"""
    sampling_feature_id = sampling_feature_code_to_id(sampling_feature_code)
    if sampling_feature_id is None: return {}
    
    query = (sqlalchemy.select(odm2_models.FeatureActions, odm2_models.Actions)
        .join(odm2_models.Actions, odm2_models.FeatureActions.actionid == odm2_models.Actions.actionid)
        .where(odm2_models.FeatureActions.samplingfeatureid == sampling_feature_id)
        .where(odm2_models.Actions.methodid == 1)
        #.order_by(odm2_models.Actions.begindatetime)
        )
    result = odm2_engine.read_query(query, output_format='dict')
    result.append({"actionid":-999, "begindatetime": "7/27/2022"}) #add a bogus survey
    return result


def delete_streamwatch_assessment(action_id:int) -> None:
    """Deletes a StreamWatch assessment from the database based on the parent action id"""
    odm2_engine.delete_object(odm2_models.Actions, action_id)


FieldConfig = namedtuple('FieldConfig', ['variable_identifier','adapter_class','units','medium'])


class CATParameter:
    def __init__(self, parameter:str=None, measurement:float=None, unit:int=None) -> None:
        self.parameter= parameter
        self.measurement= measurement
        self.unit= unit


class CATMeasurement:
        def __init__(self, name:str=None, id:str=None ,cal_date:datetime=None) -> None:
            self.name= name
            self.id=id
            self.cal_date= cal_date


class _BaseFieldAdapter():
    
    QUALITY_CODE_CV =  'None'
    PROCESSING_LEVEL = 1 #indicating raw results
    VALUE_FIELD_NAME = '' #database field to return from read method

    @classmethod
    def create_result(cls, feature_action_id:int, config:FieldConfig, result_type:str, variable_id:int=None) -> int:
        """Create a ODM2 result record"""
        result = odm2_models.Results()
        result.featureactionid = feature_action_id
        result.resulttypecv = result_type
        result.variableid = variable_id if variable_id else config.variable_id
        result.unitsid = config.units
        result.processinglevelid = cls.PROCESSING_LEVEL
        result.sampledmediumcv = config.medium
        result.valuecount = -9999
        return odm2_engine.create_object(result)

    @classmethod
    def read(cls, database_record:Dict[str, Any]) -> Any:
        return database_record[cls.VALUE_FIELD_NAME]

    @classmethod
    def get_result_records(cls, action_id:int, variable_id:int=None, variable_type_cv:str=None) -> List[str,Any]:
        query = (sqlalchemy.Select(odm2_models.Result)
            .join(odm2_models.FeatureActions, odm2_models.FeatureActions.featureaction==odm2_models.Results.featureactionid)
            .join(odm2_models.Variables, odm2_models.Variables.variableid==odm2_models.Results.variableid)
            .where(odm2_models.FeatureActions.actionid==action_id)
            )
        if variable_id: 
            query = query.where(odm2_models.Results.variableid == variable_id)
        if variable_type_cv: 
            query = query.where(odm2_models.Variables.variabletypecv == variable_type_cv)
        results = odm2_engine.read_query(query, output_format='dict')
        return results

        
class _ChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating single select field data into ODM2 results structure
    
        Implemented through the `results` table. Presence of a result record means a field
        was populated, and the `variableid` of the result record indicates the categorical value
        that was selected. 
    """

    RESULT_TYPE_CV = 'Category observation'
    VALUE_FIELD_NAME = 'variableid'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV, value)
    
    @classmethod
    def update(cls, value:Any, action_id:int, config:FieldConfig) -> None:
        result_records = cls.get_result_records(action_id, config.variable_identifier)
        if not result_records: 
            raise KeyError(f"No result records for action_id:{action_id} and variableid:{config.variable_identifier}")
        result_id = result_records[0]['resultid']
        odm2_engine.update_object(odm2_models.Results, result_id, {'variableid':value})   


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
    
    RESULT_TYPE_CV = 'Category observation'
    VALUE_FIELD_NAME = 'variableid'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        for selected in value:
            cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV, selected) 

    @classmethod
    def update(cls, value:Any, action_id:int, config:FieldConfig) -> None:
        result_records = cls.get_result_records(action_id, config.variable_identifier)
        if not result_records: 
            raise KeyError(f"No result records for action_id:{action_id} and variableid:{config.variable_identifier}")
        
        #TODO - finish implementation
        # general approach - two list/hashmap 
        #   variables in result_records
        #   variables in value argument
        # if variable in both: do nothing
        # if variable only in value argument create record new record
        #       probably need mechanism to fetch parent action datetime and utc_offset
        # if variable only in result_records: delete record

        raise NotImplementedError   


class _FloatFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating float value into ODM2 results structure
    
        Implemented through the `MeasurementResults` and `MeasurementResultValues` tables. 
    """
    
    RESULT_TYPE_CV = 'Measurement'
    AGGREGATION_STATICS_CV = 'Sporadic'
    TIME_AGGREGATION_INTERVAL = 1.0
    TIME_AGGREGATION_INTERVAL_UNIT_ID = 2 #hour minute
    VALUE_FIELD_NAME = 'measurement_datavalue'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV)
        
        measurementresult = odm2_models.MeasurementResults
        measurementresult.resultid = result_id
        measurementresult.qualitycodecv = cls.QUALITY_CODE_CV
        measurementresult.aggregationstatisticcv = cls.AGGREGATION_STATISTIC_CV
        measurementresult.timeaggregationinterval = cls.TIME_AGGREGATION_INTERVAL
        measurementresult.timeaggregationintervalunitsid = cls.TIME_AGGREGATION_INTERVAL_UNIT_ID
        odm2_engine.create_object(measurementresult, preserve_pkey=True)

        measurementresultvalue = odm2_models.MeasurementResultValues    
        measurementresultvalue.resultid = result_id
        measurementresultvalue.datavalue = value
        measurementresultvalue.valuedatetime = datetime
        measurementresultvalue.valuedatetimeutcoffset = utc_offset
        odm2_engine.create_object(measurementresultvalue)    
    
    @classmethod
    def update(cls, value:Any, action_id:int, config:FieldConfig) -> None:
        result_records = cls.get_result_records(action_id, config.variable_identifier)
        if not result_records: 
            raise KeyError(f"No result records for action_id:{action_id} and variableid:{config.variable_identifier}")
        result_id = result_records[0]['resultid']
        odm2_engine.update_object(odm2_models.MeasurementResultValues, result_id, {'datavalue':value})


class _TextFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating string value into ODM2 results structure
    
       Implemented through the `CategoricalResults` and `CategoricalResultValues` tables. 
    """
    
    RESULT_TYPE_CV = 'Category observation'
    VALUE_FIELD_NAME = 'categorical_datavalue'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV)
        
        categoricalresult = odm2_models.CategoricalResults
        categoricalresult.resultid = result_id
        categoricalresult.qualitycodecv = cls.QUALITY_CODE_CV
        odm2_engine.create_object(categoricalresult, preserve_pkey=True)

        categoricalresultvalue = odm2_models.CategoricalResultValues
        categoricalresultvalue.resultid = result_id
        categoricalresultvalue.datavalue = value
        categoricalresultvalue.valuedatetime = datetime
        categoricalresultvalue.valuedatetimeutcoffset = utc_offset
        odm2_engine.create_object(categoricalresultvalue)
    
    @classmethod
    def update(cls, value:Any, action_id:int, config:FieldConfig) -> None:
        result_records = cls.get_result_records(action_id, config.variable_identifier)
        if not result_records: 
            raise KeyError(f"No result records for action_id:{action_id} and variableid:{config.variable_identifier}")
        result_id = result_records[0]['resultid']
        odm2_engine.update_object(odm2_models.CategoricalResultValues, result_id, {'datavalue':value})   


class StreamWatchODM2Adapter():
    """Adapter class for translating stream watch form data in and out of ODM2"""

    ROOT_METHOD_ID = 1
    PARENT_ACTION_TYPE_CV = 'Field activity'
    VARIABLE_CODE = 'variablecode'
    VARIABLE_TYPE = 'variabletypecv'

    #This is intended be more flexible way to map form field ODM2 data
    #FieldConfig variable_identifier, adapterclass, units, medium
    #TODO - flesh out crosswalk with AKA
    PARAMETER_CROSSWALK = {
        'algae_amount' : FieldConfig('algaeAmount',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'algae_type' : FieldConfig('algaeType',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        'aquatic_veg_amount' : FieldConfig('aquaticVegetation',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'aquatic_veg_typ' : FieldConfig('aquaticVegetationType',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        'site_observation' : FieldConfig('commentSite',_TextFieldAdapter,499,11),
        #'simple_woody_debris_amt' : FieldConfig('????',_ChoiceFieldAdapter,1,2),
        #'simple_woody_debris_type' : FieldConfig('????',_MultiChoiceFieldAdapter,1,2),
        #'simple_land_use' : FieldConfig('????',_MultiChoiceFieldAdapter,1,2),
        'surface_coating' : FieldConfig('surfaceCoating',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        'time_since_last_precip' : FieldConfig('precipitation',_ChoiceFieldAdapter,394,'Other'),
        'turbidity_obs' : FieldConfig('turbidity',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'water_color' : FieldConfig('waterColor',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'water_movement' : FieldConfig('waterMovement',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'water_odor' : FieldConfig('waterOdor',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        'weather_cond' : FieldConfig('weather',_MultiChoiceFieldAdapter,395,'Air'),
    }

    def __init__(self, sampling_feature_id:int) -> None:
        self.sampling_feature_id = sampling_feature_id
        self._attributes = {}

    @classmethod
    def _reverse_crosswalk(cls) -> Dict[str,Any]:
        return {v[0]:(k,*v[1:]) for k,v in cls.PARAMETER_CROSSWALK.items() }

    @classmethod 
    def from_action_id(cls, feature_action_id:int, action_id:int) -> "StreamWatchODM2Adapter":
        """Constructor to retrieve existing form data from database based on assessment ActionId.
        
        input:
            action_id:int - the `actionid` corresponding to the root action for the StreamWatch assessment.
        
        output:
            StreamWatchODM2Adapter object
        """
        
        #TODO - fix implementation
        if action_id ==-999:
            return streamwatch_data
        
        instance = cls(feature_action_id)
        data = instance._read_from_database(action_id)
        instance._map_database_to_dict(data)
        return instance

    def _read_from_database(self, parent_action_id:int) -> List[Dict[str,Any]]:
        """Helper method to query the data from the database"""
        query = (
            sqlalchemy.select(
                odm2_models.Actions, odm2_models.FeatureActions, odm2_models.Results, odm2_models.Variables,
                odm2_models.MeasurementResultValues.datavalue.label('measurement_datavalue'), 
                odm2_models.CategoricalResultValues.datavalue.label('categorical_datavalue')
                )
            .join(odm2_models.FeatureActions, odm2_models.FeatureActions.actionid==odm2_models.Actions.actionid)
            .join(odm2_models.Results, odm2_models.Results.featureactionid==odm2_models.FeatureActions.featureactionid)
            .join(odm2_models.Variables, odm2_models.Variables.variableid==odm2_models.Results.variableid)
            .outerjoin(odm2_models.MeasurementResults, odm2_models.MeasurementResults.resultid==odm2_models.Results.resultid)
            .outerjoin(odm2_models.MeasurementResultValues, odm2_models.MeasurementResultValues.resultid==odm2_models.MeasurementResults.resultid)
            .outerjoin(odm2_models.CategoricalResults, odm2_models.CategoricalResults.resultid==odm2_models.Results.resultid)
            .outerjoin(odm2_models.CategoricalResultValues, odm2_models.CategoricalResultValues.resultid==odm2_models.CategoricalResults.resultid)
            .where(odm2_models.Actions.actionid==parent_action_id) #TODO: this eventually need to be scaled to include related actions
            )
        data = odm2_engine.read_query(query, output_format='dict')
        return data

    def _map_database_to_dict(self, data:Dict[str,Any]) -> None:
        """Reverses the database crosswalk to map data back to dictionary""" 

        self._map_database_to_dict_special_cases(data)
        crosswalk = self._reverse_crosswalk()
        for record in data:
            if record[self.VARIABLE_CODE] in crosswalk:
                parameter_information = crosswalk[record[self.VARIABLE_CODE]]
                field_adapter = parameter_information[1]
                self._attributes[parameter_information[0]] = field_adapter.read(record)
            elif record[self.VARIABLE_TYPE] in crosswalk:
                parameter_information = crosswalk[record[self.VARIABLE_TYPE]]
                field_adapter = parameter_information[1]
                if field_adapter is _MultiChoiceFieldAdapter:
                    if parameter_information[0] not in self._attributes: 
                        self._attributes[parameter_information[0]] = []
                    self._attributes[parameter_information[0]].append(field_adapter.read(record))
                else: 
                    self._attributes[parameter_information[0]] = field_adapter.read(record)

    def _map_database_to_dict_special_cases(self, data:Dict[str,Any]) -> None:
        pass

    def _create_feature_action(self, actionid:int) -> int:
        """Helper method to register an action to the SamplingFeature"""
        featureaction = odm2_models.FeatureActions.from_dict({
            'samplingfeatureid':self.sampling_feature_id, 
            'actionid':actionid
            })
        return odm2_engine.create_object(featureaction)

    @classmethod
    def from_dict(cls, form_data:Dict[str,Any]) -> "StreamWatchODM2Adapter":
        """Constructor to create new entry for a form on initial submittal
        
        inputs: 
            form_data:Dict[str,Any] = a dictionary of data containing the form parameters
                with the dictionary key being the form field name, and the dictionary value
                being the user input value of the field from the form. 

        output: 
            StreamWatchODM2Adapter object
        """
        
        def create_parent_action(form_data:Dict[str,Any]) -> None:
            """Helper method to create a parent a new action StreamWatch parent action"""
            #TODO - check with Anthony on efficiently adding user information
            #TODO - check with Anthony on how to best store selected activity information
            action = odm2_models.Actions()
            action.actiontypecv = cls.PARENT_ACTION_TYPE_CV
            action.methodid = cls.ROOT_METHOD_ID
            action.begindatetime = datetime.datetime.now()
            action.begindatetimeutcoffset = -5
            action.actionid = odm2_engine.create_object(action)
            return action
        
        sampling_feature_id = form_data['sampling_feature_id']
        instance = StreamWatchODM2Adapter(sampling_feature_id)
        parent_action = create_parent_action(form_data)
        feature_action_id = instance._create_feature_action(parent_action.actionid)
        for key, value in form_data.items():
            if key not in instance.PARAMETER_CROSSWALK: continue
            config = instance.PARAMETER_CROSSWALK[key]
            config.adapter_class.create(
                value, 
                parent_action.begindatetime, 
                parent_action.begindatetimeutcoffset, 
                feature_action_id,
                config
            )    
        return instance

    def to_dict(self) -> Dict[str,Any]:
        """Return attributes as dictionary with form fields mapped as keys and user inputs as values
        
            inputs: 
                None

            outputs:
                Dict[str,Any]: Dictionary of form data with form field names mapped as keys and 
                    user inputs mapped to dictionary values. 
        """
        return self._attributes()

    def update_from_dict(self, form_data:Dict[str,Any]) -> None:
        """Method to take dictionary of data from the form and update the database records
        
            inputs: 
                Dict[str,Any]: Dictionary of form data with form field names mapped as keys and
                    user inputs mapped to dictionary values.
            
            outputs:
                None
        """
        for key, value in form_data.items():
            if key in self._attributes:
                if value == self._attributes[key]: continue
                self._update_parameter(key, value)
            else:
                #Handles situationally populated fields that might not have been initially checked
                config = self.PARAMETER_CROSSWALK[key]
                config.adapter_class.create(value, self.action_id, config)
        
    def _update_parameter(self, field:str, value:Any) -> None:
        if field in self.PARAMETER_CROSSWALK:
            config = self.PARAMETER_CROSS[field]
            return config.adapter_class.update(value, self.action_id, config)
        #PRT - TODO still need to resolve how to efficiently update parameters that are not
        # handled by the adapter classes. Further discussion needed with dev team
        # One though is a hashmap of special case update methods and then 
        #   if not in hashmap use field adapter update method 
        return None








#PRT -> temporary data delete once fully implemented
streamwatch_data ={}
streamwatch_data['action_id'] = -999
streamwatch_data['sampling_feature_code'] = 'Some Site Id'
streamwatch_data['investigator1'] ='John Doe'
streamwatch_data['investigator2'] ='Jane Doe'
streamwatch_data['collect_date']='6/1/2022'
streamwatch_data['project_name']='Superman #1'
streamwatch_data['reach_length']='2 miles'
streamwatch_data['weather_cond']='Cloudy'
streamwatch_data['time_since_last_precip']='10 hrs'
streamwatch_data['water_color']='Clear'
streamwatch_data['water_odor']='Normal'

streamwatch_data['turbidity_obs']='Clear'
streamwatch_data['water_movement']='Swift/Waves'
streamwatch_data['aquatic_veg_amount']='Scarce'
streamwatch_data['aquatic_veg_type']='Submergent'
streamwatch_data['surface_coating']='None'
streamwatch_data['algae_amount']='Scarce'
streamwatch_data['algae_type']='Filamentous'
streamwatch_data['site_observation']='Some comments on and on...'

streamwatch_data['CAT_measurements']=[]


par1 = []
par1.append(CATParameter("Air temperature", 15, "C"))
par1.append(CATParameter("Dissolved oxygen", 6.5, "mg/L"))
par1.append(CATParameter("Phosphorus", 9.5, "ug/L"))
meas1 = CATMeasurement("YSI1","4531","06/13/2011")
meas1.pars = par1
streamwatch_data['CAT_measurements'].append(meas1)

par2 = []
par2.append(CATParameter("Air temperature", 16, "C"))
par2.append(CATParameter("Dissolved oxygen", 7.5, "mg/L"))
par2.append(CATParameter("Phosphorus", 6.5, "ug/L"))
meas2 = CATMeasurement("YSI2","4555","10/30/2007")
meas2.pars = par2

streamwatch_data['CAT_measurements'].append(meas2)