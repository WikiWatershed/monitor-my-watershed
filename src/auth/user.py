from auth.base_user import User
from typing import Any, Union
from collections.abc import Mapping
from sqlalchemy.orm import Query

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
        instance._username = str(mapping['username'])
        instance._isactive = bool(mapping['active'])
        instance._email = str(mapping['accountemail'])
        instance._first_name = str(mapping['accountfirstname'])
        instance._last_name = str(mapping['accountlastname'])
        return instance

    @classmethod
    def create_new_user(cls, mapping:Mapping[str,Any]) -> "User":
        """Creates a new user in the ODM2 Accounts table using Amazon Cognito fields as the mapping"""
        user = models.Accounts()
        user.username = mapping['sub']
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
        query = Query(accounts).filter(accounts.username==cognitoid)
        user_dict = odm2_engine.read_query(query, output_format='dict', orient='records')

        # if the account exists, instantiate an ODM2User object
        if len(user_dict) > 0:
            return cls.from_mapping(user_dict[0])
        return None

    @classmethod
    def from_userid(cls, userid:Union[int, str]) -> Union["User", None]:   
        """Takes a userid (accountid in ODM2) and queries for user record then returns a User instance"""
        # takes pkey for account record query accounts database table 
        accounts_model = models.Accounts
        user_dict = odm2_engine.read_object(accounts_model, userid)

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
    
    @user_id.setter
    def user_id(self, value):
        self._user_id = value

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


