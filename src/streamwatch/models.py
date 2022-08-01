from dataclasses import Field

from django import conf
from odm2 import odm2datamodels
odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models

import sqlalchemy

from collections import namedtuple 
from typing import Dict, Any, Iterable, Tuple, Union

import datetime

def variable_choice_options(variable_domain_cv:str) -> Iterable[Tuple]:
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
    """"""
    
    QUALITY_CODE_CV =  'None'
    PROCESSING_LEVEL = 1 #indicating raw results

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
        
class _ChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating single select field data into ODM2 results structure
    
        Implemented through the `results` table. Presence of a result record means a field
        was populated, and the `variableid` of the result record indicates the categorical value
        that was selected. 
    """

    RESULT_TYPE_CV = 'Category observation'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        result_id = cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV, value)
    
    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _MultiChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating multi-select field into ODM2 results structure"""
    
    RESULT_TYPE_CV = 'Category observation'

    @classmethod
    def create(cls, value:Any, datetime:datetime.datetime, utc_offset:int, feature_action_id:int, config:FieldConfig) -> None:
        for selected in value:
            cls.create_result(feature_action_id, config, cls.RESULT_TYPE_CV, selected) 

    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _FloatFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating float value into ODM2 results structure"""
    
    RESULT_TYPE_CV = 'Measurement'
    AGGREGATION_STATICS_CV = 'Sporadic'
    TIME_AGGREGATION_INTERVAL = 1.0
    TIME_AGGREGATION_INTERVAL_UNIT_ID = 2 #hour minute

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
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _TextFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating string value into ODM2 results structure"""
    
    RESULT_TYPE_CV = 'Category observation'

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
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   


class StreamWatchODM2Adapter():
    """Adapter class for translating stream watch form data in and out of ODM2"""

    ROOT_METHOD_ID = 1
    PARENT_ACTION_TYPE_CV = 'Field activity'

    #This is intended be more flexible way to map form field ODM2 data
    #FieldConfig variable_identifier, adapterclass, units, medium
    #TODO - flesh out crosswalk with AKA
    PARAMETER_CROSSWALK = {
        'algae_amount' : FieldConfig('algaeAmount',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'algae_type' : FieldConfig('algaeType',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        'aquatic_veg_amount' : FieldConfig('aquaticVegetation',_ChoiceFieldAdapter,394,'Liquid aqueous'),
        'aquatic_veg_typ' : FieldConfig('aquaticVegetationType',_MultiChoiceFieldAdapter,394,'Liquid aqueous'),
        #'site_observation' : FieldConfig('????',_TextFieldAdapter,416,11),
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
    def from_action_id(cls, action_id:int) -> "StreamWatchODM2Adapter":
        """Constructor to retrieve existing form data from database based on assessment ActionId.
        
        input:
        action_id:int - the `actionid` corresponding to the root action for the StreamWatch assessment.
        
        output:
        instance of the StreamWatchODM2Adapter
        """
        if action_id ==-999:
            return streamwatch_data

        #TODO - PRT concrete implementation needed 
        #raise NotImplementedError

    def _get_from_database(self, parent_action_id:int) -> "TDB":
        """"""

    def _create_parent_action(self, form_data:Dict[str,Any]) -> None:
        """Helper method to create a parent a new action StreamWatch parent action"""
        #TODO - check with Anthony on efficiently adding user information
        #TODO - check with Anthony on how to best store selected activity information
        
        action = odm2_models.Actions()
        action.actiontypecv = self.PARENT_ACTION_TYPE_CV
        action.methodid = self.ROOT_METHOD_ID
        action.begindatetime = datetime.datetime.now()
        action.begindatetimeutcoffset = -5
        action.actionid = odm2_engine.create_object(action)
        self.parent_action = action
        

    def _create_feature_action(self, actionid:int) -> int:
        """Helper method to register an action to the SamplingFeature"""
        featureaction = odm2_models.FeatureActions.from_dict({
            'samplingfeatureid':self.sampling_feature_id, 
            'actionid':actionid
            })
        return odm2_engine.create_object(featureaction)

    @classmethod
    def from_dict(cls, form_data:Dict[str,Any]) -> "StreamWatchODM2Adapter":
        """Constructor to create new entry for a form on initial submittal"""
        sampling_feature_id = form_data['sampling_feature_id']
        instance = StreamWatchODM2Adapter(sampling_feature_id)
        instance._create_parent_action(form_data)
        feature_action_id = instance._create_feature_action(instance.parent_action.actionid)
        for key, value in form_data.items():
            if key in instance.PARAMETER_CROSSWALK:
                config = instance.PARAMETER_CROSSWALK[key]
                config.adapter_class.create(
                    value, 
                    instance.parent_action.begindatetime, 
                    instance.parent_action.begindatetimeutcoffset, 
                    feature_action_id,
                    config
                    )    
        return instance

    def to_dict(self) -> Dict[str,Any]:
        """Return attributes as dictionary with form fields mapped as keys and user inputs as values"""
        return self._attributes()

    def update_from_dict(self, form_attributes:Dict[str,Any]) -> None:
        """Method to take dictionary of attributes from the form and update the database records"""
        for key, value in form_attributes.items():
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
        return None

    @classmethod
    def _reverse_crosswalk(cls) -> Dict[str,Any]:
        return {v[0]:(k,*v[1:]) for k,v in cls.PARAMETER_CROSSWALK.items() }






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