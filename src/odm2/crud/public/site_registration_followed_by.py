from odm2 import odm2datamodels
from sqlalchemy.orm import Session


def create_site_registration_followed_by(
    site_registration_id: int,
    account_id: int,
    session: Session = odm2datamodels.odm2_engine.session_maker(),
) -> None:
    """Create a new SiteRegisteredFollowedBy record."""
    new_record = odm2datamodels.models.SiteRegisteredFollowedBy(
        site_registration_id=site_registration_id,
        account_id=account_id,
    )
    session.add(new_record)
    session.commit()


def delete_site_registration_followed_by(
    site_registration_id: int,
    account_id: int,
    session: Session = odm2datamodels.odm2_engine.session_maker(),
) -> None:
    """Delete a SiteRegisteredFollowedBy record by its ID."""
    record = (
        session.query(odm2datamodels.models.SiteRegisteredFollowedBy)
        .filter_by(site_registration_id=site_registration_id, account_id=account_id)
        .first()
    )
    if record:
        session.delete(record)
        session.commit()


def get_site_registration_followed_by(
    account_id: int,
    session: Session = odm2datamodels.odm2_engine.session_maker(),
):
    """Retrieve SiteRegisteredFollowedBy records by site_registration_id."""
    records = (
        session.query(odm2datamodels.models.SiteRegisteredFollowedBy)
        .filter_by(account_id=account_id)
        .all()
    )
    return records
