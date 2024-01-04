from collections.abc import Mapping
from typing import Any, Union, Dict, List
import datetime

from sqlalchemy.orm import Query

from accounts.base_user import User
import dataloader
from accounts.cognito_updater import CognitoUpdater
import odm2
from odm2 import odm2datamodels

models = odm2datamodels.models
odm2_engine = odm2datamodels.odm2_engine


class ODM2User(User):
    __cognito_updater = CognitoUpdater()

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "User":
        """Converts ODM2 Accounts table GET request response into a User object"""
        instance = cls()

        # define ODM2User properties using the mapping
        instance.__user_id = int(mapping["accountid"])
        instance.__cognitoid = str(mapping["cognitoid"])
        instance.__username = str(mapping["username"])
        instance.__isactive = bool(mapping["active"])
        instance.__email = str(mapping["accountemail"])
        instance.__first_name = str(mapping["accountfirstname"])
        instance.__last_name = str(mapping["accountlastname"])
        instance.__is_admin = bool(mapping["issiteadmin"])
        return instance

    @classmethod
    def create_new_user(cls, mapping: Mapping[str, Any]) -> "User":
        """Creates a new user in the ODM2 Accounts table using Amazon Cognito fields as the mapping"""
        # If there is a legacy_id in cognito this means that there is an existing account
        # which will have been carried over to the account table. This means we just need
        # to update the record
        if "custom:legacy_id" in mapping:
            user = odm2_engine.read_object(models.Accounts, mapping["custom:legacy_id"])
            user["cognitoid"] = mapping["sub"]
            odm2_engine.update_object(models.Accounts, user["accountid"], user)
            return cls.from_userid(user["accountid"])

        user = models.Accounts()
        user.cognitoid = mapping["sub"]
        user.username = mapping["preferred_username"]
        user.accountfirstname = mapping["given_name"]
        user.accountlastname = mapping["family_name"]
        user.accountemail = mapping["email"]
        user.active = True
        user.issiteadmin = False
        pkey = odm2_engine.create_object(user)

        # create affiliation record
        affiliation = models.Affiliations()
        affiliation.affiliationstartdate = datetime.datetime.now()
        affiliation.primaryemail = mapping["email"]
        affiliation.accountid = pkey
        odm2_engine.create_object(affiliation)

        return cls.from_userid(userid=pkey)

    @classmethod
    def from_cognitoid(cls, cognitoid: str) -> Union["ODM2User", None]:
        # take cognitoid (username field) and query for account record in the ODM2 database
        accounts = models.Accounts
        query = Query(accounts).filter(accounts.cognitoid == cognitoid)
        try:
            user_dict = odm2_engine.read_query(
                query, output_format="dict", orient="records"
            )
        except odm2.exceptions.ObjectNotFound as e:
            return None

        # if the account exists, instantiate an ODM2User object
        if len(user_dict) > 0:
            return cls.from_mapping(user_dict[0])
        return None

    @classmethod
    def from_userid(cls, userid: Union[int, str]) -> Union["User", None]:
        """Takes a userid (accountid in ODM2) and queries for user record then returns a User instance"""
        # takes pkey for account record query accounts database table
        accounts_model = models.Accounts
        try:
            user_dict = odm2_engine.read_object(accounts_model, userid)
        except odm2.exceptions.ObjectNotFound as e:
            return None

        # if user does not exist in the database, return none
        if len(user_dict) == 0:
            return None

        # otherwise, instantiate the user object from the dictionary as the mapping
        else:
            return cls.from_mapping(user_dict)

    def _set_access_token(self, token: str) -> None:
        """Protected method for use on backend. Sets Cognito access token"""
        self.__access_token = token

    def _get_access_token(self) -> str:
        return self.__access_token

    def __update_database_record(self, field_name: str, value: Any) -> None:
        odm2_engine.update_object(
            model=models.Accounts,
            pkey=self.user_id,
            data={field_name: value},
        )

    def __update_cognito_record(
        self, attribute_name: str, attribute_value: str
    ) -> None:
        self.__cognito_updater.update_user_attribute(
            self, attribute_name, attribute_value
        )

    # PRT - TODO: The setters should also commit changes to the database and probably
    # back to cognito. Makes me wonder if we even need settings in this context.
    # should evaluate this need and finish implementation or remove setting support.

    # primary key for postgres database. Keep as ReadOnly.
    @property
    def user_id(self):
        return self.__user_id

    # primary key for cognito. Keep as ReadOnly.
    @property
    def congitoid(self):
        return self.__congitoid

    @property
    def username(self) -> str:
        return self.__username

    @username.setter
    def username(self, value: str) -> None:
        self.__update_database_record("username", value)
        self.__username = value
        self.__update_cognito_record("preferred_username", value)

    @property
    def is_active(self):
        return self.__isactive

    @is_active.setter
    def isactive(self, value: bool):
        if isinstance(value, bool):
            self._isactive = value

    @property
    def email(self) -> str:
        return self.__email

    @email.setter
    def email(self, value: str) -> None:
        self.__update_database_record("accountemail", value)
        self.__email = value
        self.__update_cognito_record("email", value)

    @property
    def first_name(self) -> str:
        return self.__first_name

    @first_name.setter
    def first_name(self, value: str) -> None:
        self.__update_database_record("accountfirstname", value)
        self.__first_name = value
        self.__update_cognito_record("given_name", value)

    @property
    def last_name(self) -> str:
        return self.__last_name

    @last_name.setter
    def last_name(self, value: str) -> None:
        self.__update_database_record("accountlastname", value)
        self.__last_name = value
        self.__update_cognito_record("family_name", value)

    @property
    def is_authenticated(self):
        """Returns if the user is authenticated, Always False from for AnonymousUsers"""
        # should return True by default, but could also use is active field?
        return True

    def has_permission(self, permissions: str) -> bool:
        """Check if user has permission based on applications permissions implementation"""
        # return false for now
        # need to further think through permissions implementation
        return False

    def owns_site(self, sampling_feature_id: int) -> bool:
        """Given a dataloader Registration instance, checks if the registration belows to the user"""
        # TODO
        query = "SELECT * FROM dataloaderinterface_siteregistration WHERE \"SamplingFeatureID\" = '%s';"

        #presently being affiliated with site grants ownership, though this will update with permissions later

        organization_id = None
        with odm2_engine.engine.connect() as connection:
            site_registration = connection.execute(
                query, (sampling_feature_id)
            ).fetchall()
            organization_id= site_registration[0]["OrganizationID"]

        for a in self.affiliation:
            if a.organization_id == organization_id: return True
        return False

    def can_administer_site(self, sampling_feature_id: int) -> bool:
        """Given a dataloader Registration instance, checks if the user is able to administer the registration"""
        return self.is_staff or self.owns_site(sampling_feature_id)

    def _get_affiliation(self) -> Union[None, Dict]:
        query = Query(models.Affiliations).filter(
            models.Affiliations.accountid == self.user_id
        )
        try:
            affiliations = odm2_engine.read_query(
                query, output_format="dict", orient="records"
            )
            return affiliations
        except odm2.exceptions.ObjectNotFound as e:
            return None
        except IndexError as e:
            return None

    def _get_organization(self) -> List[Dict]:
        organization_ids = [a.organization_id for a in self.affiliation]
        query = Query(models.Organizations).filter(
            models.Organizations.organizationid.in_(organization_ids)
        )
        try:
            organizations = odm2_engine.read_query(
                query, output_format="dict", orient="records"
            )
            return organizations
        except odm2.exceptions.ObjectNotFound as e:
            return None
        except IndexError as e:
            return None

    @property
    def affiliation_id(self) -> Union[List[int], None]:
        affiliation = self._get_affiliation()
        if not affiliation:
            return None
        return [a['affiliationid'] for a in affiliation]

    @property
    def organization_code(self) -> List[str]:
        organizations = self._get_organization()
        if organizations is None:
            return []
        return [o["organizationcode"] for o in organizations]

    @property
    def organization_name(self) -> List[str]:
        organizations = self._get_organization()
        if organizations is None:
            return []
        return [o["organizationname"] for o in organizations]

    @property
    def organization_id(self) -> List[int]:
        organizations = self._get_organization()
        if organizations is None:
            return []
        return [o["organizationid"] for o in organizations]

    @organization_id.setter
    def organization_id(self, value: int) -> None:
        # TODO: verify that all users get a base affiliation record on account creation
        affiliation_id = self.affiliation_id
        odm2_engine.update_object(
            models.Affiliations, affiliation_id, {"organizationid": value}
        )

    @property
    def affiliation(self) -> List["Affiliation"]:
        if not self.affiliation_id:
            return []
        return list(dataloader.models.Affiliation.objects.filter(pk__in=self.affiliation_id).all())

    @property
    def is_staff(self) -> bool:
        return self.__is_admin

    def has_perm(self, perm, obj=None):
        return self.__is_admin

    def has_module_perms(self, app_label):
        return self.__is_admin

    @property
    def pk(self):
        return self.id
