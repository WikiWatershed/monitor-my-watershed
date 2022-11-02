from django.db import models
from auth.base_user import BaseUser
from auth.backend import CognitoBackend

#DEPRECATED: Work on revising code to use auth.user.ODM2User class
#TODO: 
class Account(models.Model):
    accountid = models.IntegerField(primary_key=True)
    cognitoid = models.CharField()
    accountemail = models.CharField()
    accountfirstname = models.CharField()
    accountmiddlename = models.CharField()
    accountlastname = models.CharField()
    active = models.BooleanField()
    issiteadmin = models.BooleanField()

    def get_user(self) -> BaseUser:
        """Helper method to convert an account record to the corresponding User object"""
        user = CognitoBackend.init_user_from_id(self.accountid)
        return user

    class Meta:
        db_table=f'odm2.accounts'

