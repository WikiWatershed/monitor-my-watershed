from accounts.base_user import User
from typing import Any
from typing import Union
from typing import Dict

from collections.abc import Mapping
from sqlalchemy.orm import Query

import dataloaderinterface
import dataloader

import odm2
from odm2 import odm2datamodels
models = odm2datamodels.models
odm2_engine = odm2datamodels.odm2_engine

class ODM2User(User):

    @classmethod
    def from_mapping(cls, mapping:Mapping[str, Any]) -> "User":
        """Converts ODM2 Accounts table GET request response into a User object"""
        instance = cls()
        
        # define ODM2User properties using the mapping
        instance._user_id = int(mapping['accountid'])
        instance._cognitoid = str(mapping['cognitoid'])
        instance._username = str(mapping['username'])
        instance._isactive = bool(mapping['active'])
        instance._email = str(mapping['accountemail'])
        instance._first_name = str(mapping['accountfirstname'])
        instance._last_name = str(mapping['accountlastname'])
        instance._is_admin = bool(mapping['issiteadmin'])
        return instance

    @classmethod
    def create_new_user(cls, mapping:Mapping[str,Any]) -> "User":
        """Creates a new user in the ODM2 Accounts table using Amazon Cognito fields as the mapping"""
        #If there is a legacy_id in cognito this means that there is an existing account
        #which will have been carried over to the account table. This means we just need 
        #to update the record
        if 'custom:legacy_id' in mapping:
            user = odm2_engine.read_object(models.Accounts,mapping['custom:legacy_id'])
            user['cognitoid'] = mapping['sub']
            odm2_engine.update_object(models.Accounts,user['accountid'],user)
            return cls.from_userid(user['accountid'])
        
        user = models.Accounts()
        user.cognitoid = mapping['sub']
        user.username = mapping['preferred_username']
        user.accountfirstname = mapping['given_name']
        user.accountlastname = mapping['family_name']
        user.accountemail = mapping['email']
        user.active = True
        user.issiteadmin = False
        pkey = odm2_engine.create_object(user)
        return cls.from_userid(userid=pkey)

    @classmethod
    def from_cognitoid(cls, cognitoid:str) -> Union["ODM2User", None]:
        # take cognitoid (username field) and query for account record in the ODM2 database
        accounts = models.Accounts
        query = Query(accounts).filter(accounts.cognitoid == cognitoid)
        try:
            user_dict = odm2_engine.read_query(query, output_format='dict', orient='records')
        except odm2.exceptions.ObjectNotFound as e:
            return None

        # if the account exists, instantiate an ODM2User object
        if len(user_dict) > 0:
            return cls.from_mapping(user_dict[0])
        return None

    @classmethod
    def from_userid(cls, userid:Union[int, str]) -> Union["User", None]:   
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

    #PRT - TODO: The setters should also commit changes to the database and probably 
    # back to cognito. Makes me wonder if we even need settings in this context.
    # should evaluate this need and finish implementation or remove setting support.  
    @property
    def user_id(self):
        return self._user_id

    @property
    def congitoid(self):
        return self._congitoid

    @property
    def username(self):
        return self._username
    
    @username.setter
    def username(self, value):
        self._username = value

    @property
    def is_active(self):
        return self._isactive
    
    @is_active.setter
    def isactive(self, value):
        if isinstance(value, bool):
            self._isactive = value

    @property
    def email(self):
        return self._email
    
    @email.setter
    def email(self, value):
        self._email = value

    @property
    def first_name(self):
        return self._first_name
    
    @first_name.setter
    def first_name(self, value):
        self._first_name = value

    @property
    def last_name(self):
        return self._last_name
    
    @last_name.setter
    def last_name(self, value):
        self._last_name = value

    @property
    def is_authenticated(self):
        """Returns if the user is authenticated, Always False from for AnonymousUsers"""
        # should return True by default, but could also use is active field?
        return True

    def has_permission(self, permissions:str) -> bool:
        """Check if user has permission based on applications permissions implementation"""
        # return false for now
        # need to further think through permissions implementation
        return False

    def owns_site(self, sampling_feature_id:int) -> bool:
        """Given a dataloader Registration instance, checks if the registration belows to the user"""
        #TODO 
        query = "SELECT * FROM dataloaderinterface_siteregistration WHERE \"SamplingFeatureID\" = '%s';"
        with odm2_engine.engine.connect() as connection:
            site_registration = connection.execute(query, (sampling_feature_id)).fetchall()
            return site_registration[0]['account_id'] == self.user_id
        return False

    def can_administer_site(self, sampling_feature_id:int) -> bool:
        """Given a dataloader Registration instance, checks if the user is able to administer the registration"""
        return self.is_staff or self.owns_site(sampling_feature_id)

    def _get_affiliation(self) -> Union[None,Dict]:
        query = Query(models.Affiliations).filter(models.Affiliations.accountid == self.user_id)
        try:
            affiliations = odm2_engine.read_query(query, output_format='dict', orient='records')
            first_affiliation = affiliations[0]
            return first_affiliation
        except odm2.exceptions.ObjectNotFound as e:
            return None
        except IndexError as e:       
            return None

    @property
    def affiliation_id(self) -> Union[int,None]:    
        affiliation = self._get_affiliation()
        if affiliation is None: return None
        return affiliation['affiliationid']

    @property
    def organization_code(self) -> str:
        affiliation = self._get_affiliation()
        if affiliation is None: return ""
        organization = odm2_engine.read_object(models.Organization, affiliation.affiliationid)
        return organization.organizationcode

    @property
    def organization_name(self) -> str:
        affiliation = self._get_affiliation()
        if affiliation is None: return ""
        organization = odm2_engine.read_object(models.Organization, affiliation.affiliationid)
        return organization.organizationname

    @property
    def affiliation(self) -> Union["Affiliation", None]: 
        affiliation_id = self.affiliation_id
        if not affiliation_id: return None
        return dataloader.models.Affiliation.objects.get(pk=self.affiliation_id)
    
    @property
    def is_staff(self) -> bool:
        return self._is_admin
