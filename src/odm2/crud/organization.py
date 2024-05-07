from datetime import datetime

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from odm2 import odm2datamodels

models = odm2datamodels.models
session = odm2datamodels.odm2_engine.session_maker

def create_individual_organization(
    account: models.Accounts,
    session: Session = session(),
) -> None:
    #create organization model
    organization = models.Organizations()
    organization.organizationtypecv = 'Individual'
    organization.organizationcode = f'individual_org_account_{account.accountid}'
    organization.organizationname = f'individual_org_account_{account.accountid}'

    #create organization record
    session.add(organization)
    session.commit()
    
    #make affiliation record to tie new organization to account
    affiliation = models.Affiliations()
    affiliation.organizationid=organization.organizationid
    affiliation.isprimaryorganizationcontact=True
    affiliation.affiliationstartdate = datetime.today()
    affiliation.primaryemail = account.accountemail
    affiliation.accountid = account.accountid

    #add record to database
    session.add(affiliation)
    session.commit()

def read_organization_names(
    session: Session = session(), 
    organization_ids:Optional[List[int]]=None,
) -> List[Tuple[int,str]]:
    subquery = (
        session.query(
            models.Organizations.organizationid,
            models.Accounts.accountid,
            models.Accounts.accountfirstname,
            models.Accounts.accountlastname,
            models.Accounts.accountemail,
        )
        .join(
            models.Affiliations,
            models.Affiliations.organizationid == models.Organizations.organizationid,
        )
        .join(
            models.Accounts,
            models.Accounts.accountid == models.Affiliations.accountid,
        )
        .filter(
            models.Organizations.organizationtypecv == 'Individual'
        )
    ).subquery()
    query = (
        session.query(
            models.Organizations.organizationid,
            models.Organizations.organizationname,
            models.Organizations.organizationtypecv,
            subquery.c.accountid,
            subquery.c.accountfirstname,
            subquery.c.accountlastname,
            subquery.c.accountemail,
        )
        .outerjoin(subquery, subquery.c.organizationid == models.Organizations.organizationid)
    )
    if organization_ids:
        query = query.filter(models.Organizations.organizationid.in_(organization_ids))

    results = query.all()
    return results