from sqlalchemy.orm import Session

from odm2 import odm2datamodels

models = odm2datamodels.models
session = odm2datamodels.odm2_engine.session_maker


def read_account_affiliations(session: Session = session()):
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
    return query.all()
