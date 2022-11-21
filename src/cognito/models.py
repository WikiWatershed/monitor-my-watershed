from django.db import models
from cognito.base_user import User
from cognito.backend import CognitoBackend

#DEPRECATED: Work on revising code to use cognito.user.ODM2User class
#TODO: 
class Account(models.Model):
    accountid = models.IntegerField(primary_key=True)   
    cognitoid = models.CharField(max_length=255)
    accountemail = models.CharField(max_length=255)
    accountfirstname = models.CharField(max_length=255)
    accountmiddlename = models.CharField(max_length=255)
    accountlastname = models.CharField(max_length=255)
    active = models.BooleanField()
    issiteadmin = models.BooleanField()

    def get_user(self) -> User:
        """Helper method to convert an account record to the corresponding User object"""
        user = CognitoBackend.init_user_from_id(self.accountid)
        return user

    class Meta:
        db_table=f'odm2.accounts'

