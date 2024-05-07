from typing import List
from sqlalchemy.orm import Session

from odm2 import odm2datamodels

models = odm2datamodels.models
session = odm2datamodels.odm2_engine.session_maker


def read_account_affiliations(session: Session = session(), organizations:List[int]=None):
    query = (
        # session.query(models.Affiliations.affiliationid)
        # .join(
        #    models.Accounts, models.Accounts.accountid == models.Affiliations.accountid
        # )
        # .order_by(models.Accounts.accountlastname)
        session.query(
            models.Affiliations.affiliationid,
            models.Accounts.accountfirstname,
            models.Accounts.accountlastname,
            models.Organizations.organizationname,
            models.Organizations.organizationtypecv,
        )
        .join(
            models.Affiliations,
            models.Affiliations.accountid == models.Accounts.accountid,
        )
        .outerjoin(
            models.Organizations,
            models.Organizations.organizationid == models.Affiliations.organizationid,
        )
        .order_by(models.Accounts.accountlastname)
    )
    if organizations:
        query = query.filter(
            models.Organizations.organizationid.in_(organizations)
        )
    return query.all()
