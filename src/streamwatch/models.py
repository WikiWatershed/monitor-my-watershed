from odm2 import odm2datamodels
odm2_engine = odm2datamodels.odm2_engine
odm2_models = odm2datamodels.models

import sqlalchemy

from typing import Dict, Any, Iterable, Tuple

def variable_choice_options(variable_domain_cv:str) -> Iterable[Tuple]:
    query = (sqlalchemy.select(odm2_models.Variables.variablecode, odm2_models.Variables.variabledefinition)
            .where(odm2_models.Variables.variabletypecv == variable_domain_cv)
        )
    records = odm2_engine.read_query(query, output_format='records')
    
    return records


