from sqlalchemy import Column, Integer
from sqlalchemy import ForeignKey

from odm2.models.base import Base


class SiteRegisteredFollowedBy(Base):
    __tablename__ = "dataloaderinterface_siteregistration_followed_by"
    __table_args__ = ({"schema": "public"},)

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_registration_id = Column(
        "siteregistration_id",
        Integer,
        # TODO: This should be a ForeignKey to the accounts table, but the model does not map yet
        # ForeignKey("siteregistration.RegistrationID"),
        nullable=False,
    )
    account_id = Column(
        "account_id",
        Integer,
        # TODO: This should be a ForeignKey to the accounts table, but the model does not map yet
        # ForeignKey("odm2.accounts.accountid"),
        nullable=False,
    )
