import typing
import datetime

from sqlalchemy import orm
import sqlalchemy as sqla
from sqlalchemy.dialects import postgresql as pg


class TimeSeriesResults:
    """http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Results_TimeSeriesResults.html"""

    resultid: orm.Mapped[int] = sqla.Column("resultid", sqla.Integer, primary_key=True)
    xlocation: orm.Mapped[typing.Optional[float]] = sqla.Column(
        "xlocation", pg.DOUBLE_PRECISION
    )
    xlocationunitid: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "xlocationunitid", sqla.ForeignKey("units.unitsid")
    )
    ylocation: orm.Mapped[typing.Optional[float]] = sqla.Column(
        "ylocation", pg.DOUBLE_PRECISION
    )
    ylocationunitid: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "ylocationunitid", sqla.ForeignKey("units.unitsid")
    )
    zlocation: orm.Mapped[typing.Optional[float]] = sqla.Column(
        "zlocation", pg.DOUBLE_PRECISION
    )
    zlocationunitid: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "zlocationunitid", sqla.ForeignKey("units.unitsid")
    )
    spatialreferenceid: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "spatialreferenceid", sqla.Integer
    )
    intendedtimespacing: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "intendedtimespacing", pg.DOUBLE_PRECISION
    )
    intendedtimespacingunitid: orm.Mapped[typing.Optional[int]] = sqla.Column(
        "intendedtimespacingunitid", sqla.ForeignKey("units.unitsid")
    )
    aggregationstaticcv: orm.Mapped[str] = sqla.Column(
        "aggregationstaticcv", sqla.ForeignKey("cv_aggregationstatistic.term")
    )


class TimeSeriesResultValues:
    """http://odm2.github.io/ODM2/schemas/ODM2_Current/tables/ODM2Results_TimeSeriesResultValues.html"""

    valueid: orm.Mapped[int] = sqla.Column("valueid", sqla.Integer, primary_key=True)
    resultid: orm.Mapped[int] = sqla.Column(
        "resultid", sqla.ForeignKey("results.resultid")
    )
    datavalue: orm.Mapped[float] = sqla.Column("datavalue", pg.DOUBLE_PRECISION)
    valuedatetime: orm.Mapped[datetime.datetime] = sqla.Column(
        "valuedatetime", sqla.DateTime
    )
    valuedatetimeutcoffset: orm.Mapped[int] = sqla.Column(
        "valuedatetimeutcoffset", sqla.Integer
    )
    censorcodecv: orm.Mapped[str] = sqla.Column(
        "censorcodecv", sqla.ForeignKey("cv_censorcode.term")
    )
    qualitycodecv: orm.Mapped[str] = sqla.Column(
        "qualitycodecv", sqla.ForeignKey("cv_qualitycode.term")
    )
    timeaggregationinterval: orm.Mapped[float] = sqla.Column(
        "timeaggregationinterval", pg.DOUBLE_PRECISION
    )
    timeaggregationintervalunitsid: orm.Mapped[int] = sqla.Column(
        "timeaggregationintervalunitsid", sqla.ForeignKey("units.unitsid")
    )
