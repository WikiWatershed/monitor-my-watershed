from odm2 import odm2datamodels
odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models

import sqlalchemy

from collections import namedtuple 
from typing import Dict, Any, Iterable, Tuple, Union

import datetime

def variable_choice_options(variable_domain_cv:str) -> Iterable[Tuple]:
    query = (sqlalchemy.select(odm2_models.Variables.variablecode, odm2_models.Variables.variabledefinition)
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
    if result: return result['sampling_feature_id']
    return None

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

    def create_result(self, action_id:int, variable_id:int, units_id:int, result_type:str, medium:str) -> int:
        """Create a result record"""
        with odm2_engine.session_maker() as session:
            result = odm2_models.Result()
            result.featureactionid = action_id
            result.resulttypecy = result_type
            result.variableid = variable_id
            result.units = units_id
            result.processinglevelid = 1
            result.sampledmediumcv = medium
            result.valuecount = -9999
            session.add(result)
            session.commit()
            return result.resultid

class _ChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating single select field data into ODM2 results structure"""
    
    @classmethod
    def create(cls, value:Any, feature_action_id:int, config:FieldConfig) -> None:
        raise NotImplementedError    
    
    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _MultiChoiceFieldAdapter(_BaseFieldAdapter):
    """Adapter class for translating multi-select field into ODM2 results structure"""

    @classmethod
    def create(cls, value:Any, feature_action_id:int, config:FieldConfig) -> None:
        raise NotImplementedError 

    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _FloatFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating float value into ODM2 results structure"""

    @classmethod
    def create(cls, value:Any, feature_action_id:int, config:FieldConfig) -> None:
        raise NotImplementedError    
    
    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   

class _TextFieldAdapter(_BaseFieldAdapter):
    """Adapter for translating string value into ODM2 results structure"""

    @classmethod
    def create(cls, value:Any, feature_action_id:int, config:FieldConfig) -> None:
        raise NotImplementedError    
    
    @classmethod
    def update(cls, value:Any, result_id:int, config:FieldConfig) -> None:
        raise NotImplementedError   


class StreamWatchODM2Adapter():
    """Adapter class for translating stream watch form data in and out of ODM2"""


    #This is intended be more flexible way to map form field ODM2 data
    #FieldConfig variable_identifier, adapterclass, units_id, medium
    #PRT - TODO - flesh out crosswalk with AKA
    parameter_crosswalk = {
        'aqautic_veg_typ' : FieldConfig('',_ChoiceFieldAdapter,1,2) #example 
    }

    def __init__(self) -> None:
        self.feature_action_id
        self._attributes = {}

    @classmethod 
    def from_action_id(cls, action_id:int) -> "StreamWatchODM2Adapter":
        """Constructor to retrieve existing form data from database based on assessment ActionId.
        
        input:
        action_id:int - the `actionid` corresponding to the root action for the StreamWatch assessment.
        
        output:
        instance of the StreamWatchODM2Adapter
        """
        return streamwatch_data

        #TODO - PRT concrete implementation needed 
        #raise NotImplementedError

    @classmethod
    def from_dict(cls, form_attributes:Dict[str,Any]) -> "StreamWatchODM2Adapter":
        """Constructor to create new entry for a form on initial submittal"""
        instance = StreamWatchODM2Adapter()
        #PRT - TODO - implement methods/logic to store variables outside of the crosswalk
        for key, value in form_attributes.items():
            if key in instance.parameter_crosswalk:
                config = instance.parameter_crosswalk[key]
                config.adapter_class.create(value, instance.feature_action_id, config)    
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
                config = self.parameter_crosswalk[key]
                config.adapter_class.create(value, self.action_id, config)
        
    def _update_parameter(self, field:str, value:Any) -> None:
        if field in self.parameter_crosswalk:
            config = self.parameter_cross[field]
            return config.adapter_class.update(value, self.action_id, config)
        #PRT - TODO still need to resolve how to efficiently update parameters that are not
        # handled by the adapter classes. Further discussion needed with dev team
        return None

    @classmethod
    def _reverse_crosswalk(cls) -> Dict[str,Any]:
        return {v[0]:(k,*v[1:]) for k,v in cls.parameter_crosswalk.items() }






#PRT -> temporary data delete once fully implemented
streamwatch_data ={}
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