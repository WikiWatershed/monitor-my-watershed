import sqlalchemy
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm import Query
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.ext.declarative import declared_attr, declarative_base

import pickle
from typing import Dict, Union, Any, Type, List
import warnings

import pandas as pd

from .exceptions import ObjectNotFound
from .automap_models import annotations
from .automap_models import core
from .automap_models import cv
from .automap_models import dataquality
from .automap_models import equipment
from .automap_models import extensionproperties
from .automap_models import externalidentifiers
from .automap_models import labanalyses
from .automap_models import provenance
from .automap_models import results
from .automap_models import samplingfeatures
from .automap_models import simulation
from .automap_models import auth

from odm2.models import results as _results
from odm2.models import public as _public

OUTPUT_FORMATS = ("json", "dataframe", "dict", "records")


class AutoBase:
    @declared_attr
    def __tablename__(self) -> str:
        cls_name = str(self.__name__)
        return cls_name.lower()

    @classmethod
    def from_dict(cls, attributes_dict: Dict) -> object:
        """Alternative constructor that uses dictionary to populate attributes"""
        instance = cls.__new__(cls)
        instance.__init__()
        for key, value in attributes_dict.items():
            if hasattr(instance, key):
                if value == "":
                    value = None
                setattr(instance, key, value)
        return instance

    def to_dict(self) -> Dict[str, Any]:
        """Converts attributes into a dictionary"""
        columns = self.__table__.columns.keys()
        output_dict = {}
        for column in columns:
            output_dict[column] = getattr(self, column)
        return output_dict

    def update_from_dict(self, attributes_dict: Dict[str, any]) -> None:
        """Updates instance attributes based on provided dictionary"""
        for key, value in attributes_dict.items():
            if hasattr(self, key):
                if value == "":
                    value = None
                setattr(self, key, value)

    @classmethod
    def get_pkey_name(cls) -> Union[str, None]:
        """Returns the primary key field name for a given model"""
        columns = cls.__table__.columns
        for column in columns:
            if column.primary_key:
                return column.name
        return None


class ODM2Engine:
    def __init__(
        self,
        session_maker: sqlalchemy.orm.sessionmaker,
        engine: sqlalchemy.engine.Engine,
    ) -> None:
        self.session_maker = session_maker
        self.engine = engine

    def read_query(
        self,
        query: Union[Query, Select],
        output_format: str = "json",
        orient: str = "records",
    ) -> Union[str, pd.DataFrame]:
        # guard against invalid output_format strings
        if output_format not in OUTPUT_FORMATS:
            raise ValueError(
                f":argument output_format={output_format}, is not a valid output_format strings: {OUTPUT_FORMATS}"
            )

        # use SQLAlchemy session to read_query and return response in the designated output_format
        with self.session_maker() as session:
            if isinstance(query, Select):
                df = pd.read_sql(query, session.bind)
            else:
                df = pd.read_sql(query.statement, session.bind)

            if output_format == "json":
                return df.to_json(orient=orient)
            elif output_format == "dataframe":
                return df
            elif output_format == "dict":
                return df.to_dict(orient=orient)
            elif output_format == "records":
                return df.to_records(index=False)
            raise TypeError("Unknown output format")

    def insert_query(self, objs: List[object]) -> None:
        with self.session_maker() as session:
            session.add_all(objs)
            session.commit()

    def create_object(
        self, obj: object, preserve_pkey: bool = False
    ) -> Union[int, str]:
        """Accepts an ORM mapped model and created a corresponding database record

        Accepts on one of the ORM mapped models and creates the corresponding database
        record, returning the primary key of the newly created record.

        Arguments:
            obj:object - The ORM mapped model
            preserve_pkey:bool - Default=False - flag indicating if the primary key for
                the object should be preserved. Avoid in general use cases where database has
                a serial that auto assigned primary key, however this can be set to True to
                specify you own the primary key value.

        Returns:
            primary key: Union[int, str]

        """

        pkey_name = obj.get_pkey_name()
        if not preserve_pkey:
            setattr(obj, pkey_name, None)

        with self.session_maker() as session:
            session.add(obj)
            session.commit()
            pkey_value = getattr(obj, pkey_name)
            return pkey_value

    def read_object(
        self,
        model: Type[AutoBase],
        pkey: Union[int, str],
        output_format: str = "dict",
        orient: str = "records",
    ) -> Dict[str, Any]:
        with self.session_maker() as session:
            obj = session.get(model, pkey)
            pkey_name = model.get_pkey_name()
            if obj is None:
                raise ObjectNotFound(
                    f"No '{model.__name__}' object found with {pkey_name} = {pkey}"
                )
            session.commit()

            # convert obj_dict to a dictionary if it isn't one already
            obj_dict = obj.to_dict()

            # guard against invalid output_format strings
            if output_format not in OUTPUT_FORMATS:
                raise ValueError(
                    f":param output_format = {output_format}, which is not one of the following valid output_format strings: {OUTPUT_FORMATS}"
                )

            if output_format == "dict":
                return obj_dict

            else:
                # convert to series if only one row
                keys = list(obj_dict.keys())
                if not isinstance(obj_dict[keys[0]], list):
                    for key in keys:
                        new_value = [obj_dict[key]]
                        obj_dict[key] = new_value

                obj_df = pd.DataFrame.from_dict(obj_dict)
                if output_format == "dataframe":
                    return obj_df
                elif output_format == "json":
                    return obj_df.to_json(orient=orient)
                raise TypeError("Unknown output format")

    def update_object(
        self, model: Type[AutoBase], pkey: Union[int, str], data: Dict[str, Any]
    ) -> None:
        if not isinstance(data, dict):
            data = data.dict()
        pkey_name = model.get_pkey_name()
        if pkey_name in data:
            data.pop(pkey_name)
        with self.session_maker() as session:
            obj = session.get(model, pkey)
            if obj is None:
                raise ObjectNotFound(
                    f"No '{model.__name__}' object found with {pkey_name} = {pkey}"
                )
            obj.update_from_dict(data)
            session.commit()
            data[pkey_name] = pkey

    def delete_object(self, model: Type[AutoBase], pkey: Union[int, str]) -> None:
        with self.session_maker() as session:
            obj = session.get(model, pkey)
            pkey_name = model.get_pkey_name()
            if obj is None:
                raise ObjectNotFound(
                    f"No '{model.__name__}' object found with {pkey_name} = {pkey}"
                )
            session.delete(obj)
            session.commit()


class Models:
    def __init__(self, base_model) -> None:
        self._base_model = base_model

        # models that are declaratively mapped.
        (self.__add_model(_results.TimeSeriesResults),)
        self.__add_model(_results.TimeSeriesResultValues)
        self.__add_model(_public.SiteRegisteredFollowedBy)

        self.__process_schema(annotations)
        self.__process_schema(core)
        self.__process_schema(cv)
        self.__process_schema(dataquality)
        self.__process_schema(equipment)
        self.__process_schema(extensionproperties)
        self.__process_schema(externalidentifiers)
        self.__process_schema(labanalyses)
        self.__process_schema(provenance)
        self.__process_schema(results)
        self.__process_schema(samplingfeatures)
        self.__process_schema(simulation)
        self.__process_schema(auth)

    def __process_schema(self, schema: str) -> None:
        classes = [c for c in dir(schema) if not c.startswith("__")]
        for class_name in classes:
            model = getattr(schema, class_name)
            # ignore modules for when a schema imports them
            if type(model) is not type:
                continue
            self.__remap_model(model)

    def __remap_model(self, model):
        base = tuple([self._base_model])
        extended_model = type(model.__name__, base, {})
        setattr(self, model.__name__, extended_model)

    def __add_model(self, model):
        setattr(self, model.__name__, model)

    def _trim_dunders(self, dictionary: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in dictionary.items() if not k.startswith("__")}


class ODM2DataModels:
    def __init__(
        self, engine: sqlalchemy.engine, schema: str = "odm2", cache_path: str = None
    ) -> None:
        self._schema = schema
        self._cache_path = cache_path

        self._engine = engine
        self._session = sqlalchemy.orm.sessionmaker(self._engine)
        self._cached = False
        self.odm2_engine: ODM2Engine = ODM2Engine(self._session, self._engine)

        self._model_base = self._prepare_model_base()
        self.models = Models(self._model_base)
        if not self._cached:
            try:
                self._prepare_automap_models()
            except sqlalchemy.exc.OperationalError:
                warnings.warn('Unable to prepare models, is database up?', RuntimeWarning)

    def _prepare_model_base(self):
        try:
            with open(self._cache_path, "rb") as file:
                metadata = pickle.load(file=file)
                self._cached = True
                return declarative_base(
                    cls=AutoBase, bind=self._engine, metadata=metadata
                )
        except FileNotFoundError:
            metadata = sqlalchemy.MetaData(schema=self._schema)
            self._cached = False
            return automap_base(cls=AutoBase, metadata=metadata)

    def _prepare_automap_models(self):
        self._model_base.prepare(self._engine)
        if not self._cache_path:
            return
        try:
            with open(self._cache_path, "wb") as file:
                pickle.dump(self._model_base.metadata, file)
        except FileNotFoundError:
            warnings.warn(
                "Unable to cache models which may lead to degraded performance.",
                RuntimeWarning,
            )
