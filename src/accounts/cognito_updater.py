import boto3 
from django.conf import settings

from accounts.base_user import User

AWS_REGION_NAME = settings.COGNITO_REGION
AWS_ACCESS_KEY_ID = settings.COGNITO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = settings.COGNITO_SECRET_ACCESS_KEY

class CognitoUpdater():

    def __init__(self) -> None:
        self._client = boto3.client('cognito-idp',
                                   region_name=AWS_REGION_NAME, 
                                   aws_access_key_id=AWS_ACCESS_KEY_ID, 
                                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
        
    def update_user_attribute(self, user:User, attribute_name:str, attribute_value:str):
        response = self._client.update_user_attributes(
            UserAttributes=[
                {
                    'Name':attribute_name,
                    'Value':attribute_value,
                }
            ],
            AccessToken=user._get_access_token(),
        )
        return 'It worked'
