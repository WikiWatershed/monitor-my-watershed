from odm2.base import _model_base

"""Data models corresponding to the tables under the ODM2Provenance schema
	Reference: http://odm2.github.io/ODM2/schemas/ODM2_Current/schemas/ODM2Provenance.html
"""

class AuthorLists(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_AuthorLists.html"""

class Citations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_Citations.html"""

class DataSetCitations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_DatasetCitations.html"""

class DerivationEquations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_DerivationEquations.html"""

class MethodCitations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_MethodCitations.html"""
	
class RelatedAnnotations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_RelatedAnnotations.html"""

class RelatedDatasets(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_RelatedDatasets.html"""

class RelatedResults(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_RelatedResults.html"""

class ResultDerivationEquations(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Provenance_ResultDerivationEquations.html"""