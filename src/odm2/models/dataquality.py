from odm2.base import _model_base

"""Data models corresponding to the tables under the ODM2DataQuality schema
	Reference: http://odm2.github.io/ODM2/schemas/ODM2_Current/schemas/ODM2DataQuality.html
"""

class DataQuality(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2DataQuality_DataQuality.html"""

class ReferenceMaterials(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2DataQuality_ReferenceMaterials.html"""

class ReferenceMaterialValues(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2DataQuality_ReferenceMaterialValues.html"""

class ResultNormalizationValues(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2DataQuality_ResultNormalizationValues.html"""

class ResultsDataQuality(_model_base):
	"""http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2DataQuality_ResultsDataQuality.html"""