from abc import ABC
from abc import abstractmethod

from typing import Union, Any, List
from collections.abc import Mapping

from warnings import warn

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
    def user_id(self) -> int:
        """Returns the user's userid (primarykey/ unique identifier used by the application)"""

    @property
    def cognitoid(self) -> str:
        """Stores the cognito unique identifier for the user account"""

    @property
    def username(self) -> str:
        """Username as it should appear on application frontend"""
    
    @property
    def first_name(self) -> str:
        """User first name"""

    @property
    def last_name(self) -> str:
        """User last name"""

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'

    @property
    def email(self) -> str:
        """User email address"""

    @property
    def is_active(self) -> bool:
        """Flag to indicate if user's account is active"""

    def has_permission(self, permissions:str) -> bool:
        """Check if user has permission based on applications permissions implementation"""

    #TODO: Eventually we would like to deprecate this method and remove the dataloader
    #models, however until the rest of the codebase is refactored we should continue to support
    #this method. Carried over from accounts.User class.
    @abstractmethod
    def owns_site(self, registration) -> bool:
        """Given a dataloader Registration instance, checks if the registration belows to the user"""

    @abstractmethod
    def can_administer_site(self, registration) -> bool:
        """Given a dataloader Registration instance, checks if the user is able to administer the registration"""

    #TODO: These are legacy properties that are carried over from the django user implementation.
    # the team should evaluate which properties need to remain and which should be gradually refactored 
    # out and replaced.

    #Hold over method to allow access to user_id through old signature
    @property
    def id(self) -> int:
        warn("`id` will be deprecated, use `User.user_id`", DeprecationWarning, stacklevel=2)
        return self.user_id 

    @property
    def affiliation_id(self) -> List[int]:    
        """"""

    @property
    def organization_code(self) -> str:
        """"""

    @property
    def organization_name(self) -> str:
        """"""

    @property
    def organization_id(self) -> List[int]:
        """"""

    @property
    def affiliation(self) -> List["Affiliation"]: 
        """"""
    
    @property
    def is_staff(self) -> bool:
        """"""


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
        return None
    
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

    def owns_site(self, registration) -> bool:
        """Given a dataloader Registration instance, checks if the registration belows to the user"""
        return False

    def can_administer_site(self, registration) -> bool:
        """Given a dataloader Registration instance, checks if the user is able to administer the registration"""
        return False

    @property
    def affiliation_id(self) -> List[int]:    
        return []

    @property
    def organization_code(self) -> str:
        return ""

    @property
    def organization_name(self) -> str:
        return ""
    
    @property
    def organization_id(self) -> str:
        return []

    @property
    def affiliation(self) -> List["Affiliation"]: 
        return []
    
    @property
    def is_staff(self) -> bool:
        return False

