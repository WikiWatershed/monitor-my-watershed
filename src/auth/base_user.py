from abc import ABC

from typing import Union, Any
from collections.abc import Mapping

class User(ABC):
    """Abstract Base Class for custom user implementations """

    @classmethod
    def from_cognitoid(cls, cognitoid:str) -> "User":
        """Takes Cognito user id and return User instance or None if user record not in database"""

    @classmethod
    def from_mapping(cls, mapping:Mapping[str,Any]) -> "User":
        """Takes a Mapping and returns a User instance
        
        Should return None if user does not exist.
        """

    @classmethod
    def from_userid(cls, userid:Union[str, int]) -> "User":
        """Takes a userid and queries for user record then returns a User instance
        
        Should return None if user does not exist.
        """

    @classmethod
    def create_new_user(cls, mapping:Mapping[str, Any]) -> "User":
        """ Constructor taking mapping from AWS response and create new Database User record"""

    @property
    def is_authenticated(self):
        """Returns if the user is authenticated, 
        
            Should be True for user's that are authenticated and False for anonymous users"""

    @property
    def user_id(self):
        """Returns the user's userid (primarykey/ unique identifier used by the application)"""

    @property
    def cognitoid(self):
        """Stores the cognito unique identifier for the user account"""

    @property
    def username(self):
        """Username as it should appear on application frontend"""
    
    @property
    def first_name(self):
        """User first name"""

    @property
    def last_name(self):
        """User last name"""

    @property
    def email(self):
        """User email address"""

    @property
    def is_active(self):
        """Flag to indicate if user's account is active"""


    def has_permission(self, permissions:str) -> bool:
        """Check if user has permission based on applications permissions implementation"""

class AnonymousUser(User):

    @classmethod
    def create_new_user(cls, mapping:Mapping[str,Any]) -> "User":
        raise NotImplementedError

    @classmethod
    def from_cognitoid(cls, cognitoid) -> "User":
        raise NotImplementedError
 
    @classmethod
    def from_mapping(cls, mapping:Mapping[str,Any]) -> "User":
        """Takes a Mapping and returns a User instance"""
        return cls()

    @classmethod
    def from_userid(cls, userid:Union[str, int]) -> "User":
        """Takes a userid and queries for user record then returns a User instance"""
        return cls()

    @property
    def is_authenticated(self):
        """Returns if the user is authenticated, Always from for AnonymousUsers"""
        return False

    @property
    def user_id(self):
        """Returns the user's userid (primarykey/ unique identifier used by the application)"""
        return ''
    
    @property
    def cognitoid(self):
        """Stores the cognito unique identifier for the user account"""
        return 'Anonymous User'

    @property
    def username(self):
        return "Anonymous User"

    @property
    def first_name(self):
        return 'Anonymous'

    @property
    def last_name(self):
        return 'User'

    @property
    def email(self):
        return ''

    @property
    def is_active(self):
        return False

    def has_permission(self, permissions:str) -> bool:
        """Check if user has permission based on applications permissions implementation"""
        return False



