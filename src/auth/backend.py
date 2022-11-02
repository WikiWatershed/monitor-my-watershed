from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.middleware.csrf import rotate_token
from django.utils.crypto import constant_time_compare
import django.http 

import requests

import boto3
import base64
import hashlib
import hmac

from typing import Union
from auth.base_user import User, AnonymousUser
from auth.user import ODM2User

# AWS Credential Info which should be specified in the application settings 
AWS_REGION_NAME = settings.COGNITO_REGION
AWS_ACCESS_KEY_ID = settings.COGNITO_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = settings.COGNITO_SECRET_ACCESS_KEY
AWS_USER_POOL_ID = settings.COGNITO_USER_POOL_ID
AWS_CLIENT_ID = settings.COGNITO_CLIENT_ID
AWS_CLIENT_SECRET = settings.COGNITO_CLIENT_SECRET
AWS_OAUTH_URL = settings.COGNITO_OAUTH_URL
AWS_REDIRECT_URL = settings.COGNITO_REDIRECT_URL
AWS_USERFIELD = 'sub'

USER_MODEL = ODM2User
ANONYMOUS_USER_MODEL = AnonymousUser

SESSION_KEY = settings.SESSION_KEY
BACKEND_SESSION_KEY = settings.BACKEND_SESSION_KEY
HASH_SESSION_KEY = settings.HASH_SESSION_KEY

def login_required(view, *args, **kwargs) -> None:
    def authenicated(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated: return view(request, *args, **kwargs)
        return django.http.HttpResponse('Unauthorized', status=401)
    return authenicated

class CognitoBackend(BaseBackend):
    """Customized UserAuth Backend to use AWS Cognito for validation in place of django user/password model"""
    def __init__(self):
        self._client = boto3.client('cognito-idp',
                                   region_name=AWS_REGION_NAME, 
                                   aws_access_key_id=AWS_ACCESS_KEY_ID, 
                                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    
    def authenticate(self, username:str=None, password:str=None, token:str=None, code:str=None) -> Union[User]:
        """
        Main method for user authenication which interfaces with AWS Cognito and exchanges provide information for Cognito username which 
        is later mapped to an application user_id. There are 3 acceptable inputs for authenications

        1) The classic 'username' and 'password' which are the user's AWS username and password which can be exchanged with AWS Cognito for an Access Token. 
            This method is not utlized by the limnos application. We instead redirect user's to a thirdparty AWS based login page. However this
            method could be used if we ever wanted to develop a user login page on this application.
        2) An AWS Authorization Code which is provided by AWS after successful authentication through their service 
            (i.e. using facebook, twitter, or username and password) at AWS login page assoicated with this application's user pool. 
            This approach is used by the callback url of the AWS login page which passes an authenication code to our 'oauth2_cognito' method 
            which in turn envokes this authenication method.
        3) An AWS User Refresh Token which can be exchanged for an Access Token and subsequently user information like username. 
            With oauth2 utlimately the other 2 authenication approaches end up through this method as the end point. 
        """
        if token is not None: return(self._authenticate_token(token))
        elif code is not None: return(self._authenticate_code(code))
        elif username is not None and password is not None: return(self._authenticate_password(username, password))

    def _authenticate_password(self, username:str, password:str) -> User:
            """Interal method - exchanges username and password for AWS Access Token."""
            self.username = username
            auth_response = self._client.initiate_auth(
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME':username,
                        'PASSWORD':password,
                        'SECRET_HASH': self._secret_hash
                    },
                    ClientId=AWS_CLIENT_ID
                )

            auth_result = auth_response.get('AuthenticationResult')
            token = auth_result.get('AccessToken')
            return (self._authenticate_token(token))

    def _authenticate_token(self,token) -> User:
        """Internal Method - Uses a user Access Token to fetch user information (primarily need username) from AWS Cognito user pool"""
        response = self._client.get_user(AccessToken=token)
        return self._init_user_response(response)

    def _authenticate_code(self, code) -> User:
        """Internal Method - Exchanges Authorization Code for User Refresh Token 
       
        see AWS doc for additional detail https://docs.aws.amazon.com/cognito/latest/developerguide/token-endpoint.html#post-token
        """
        message = AWS_CLIENT_ID+':'+AWS_CLIENT_SECRET
        authorization = base64.b64encode(message.encode('utf-8')).decode('utf-8')
        headers = {
            'Content-Type':R"application/x-www-form-urlencoded",
            'Authorization':'Basic '+ authorization,
            'Accept':'*/*'
            }
        data = {
            'grant_type':'authorization_code',    
            'client_id':AWS_CLIENT_ID,
            'code':code,
            'scope':'aws.cognito.signin.user.admin',
            'redirect_uri': AWS_REDIRECT_URL
            }
        response = requests.post(url=AWS_OAUTH_URL, headers=headers, data=data) 
        
        if response.status_code != 200:
            # error handling needed - redirect to failed login
            raise RuntimeError('Amazon returned non-valid client user response!')

        else:
            token = response.json()['access_token']
            return (self._authenticate_token(token))

    @property
    def _secret_hash(self):
        """ Internal Method - generates encryption key required by AWS Congnito"""
        message = bytearray(self.username + AWS_CLIENT_ID, 'utf-8')
        hmac_obj = hmac.new(bytearray(AWS_CLIENT_SECRET, 'utf-8'), message, hashlib.sha256)
        return base64.standard_b64encode(hmac_obj.digest()).decode('utf-8') 
        
    def _init_user_response(self, response) -> User:
        """ Internal Method - Takes AWS response and return an instance of a User 
        
        Uses the 'from_mapping' method of the User class. If the method returns a None,
        indicating no user record exists, the _create_user method will be invoked. 

        """
        user_attributes = {list(item.values())[0]:list(item.values())[1] for item in response['UserAttributes']}
        
        user = USER_MODEL.from_cognitoid(user_attributes[AWS_USERFIELD])
        if user is not None: return user

        user = USER_MODEL.create_new_user(user_attributes)
        return user

    @classmethod
    def init_user_from_id(cls, userid:Union[None,str,int] ) -> User:
        if not userid: return ANONYMOUS_USER_MODEL() 
        user = USER_MODEL.from_userid(userid)
        if user is not None: return(user)
        return ANONYMOUS_USER_MODEL()

    def login(self, request, user):
        """
        Uses session to create a persistent user_id so user doesn't need to log in after each request
        based on logic in contrib.auth.login method
        """
        session_auth_hash = ''
        if user is None:
            user = request.user
        if hasattr(user, 'get_session_auth_hash'):
            session_auth_hash = user.get_session_auth_hash()

        if SESSION_KEY in request.session:
            if request.session[SESSION_KEY] != user.user_id or ( 
                session_auth_hash and not constant_time_compare(request.session.get(HASH_SESSION_KEY, ''), session_auth_hash)):

                # create an empty session if the existing session corresponds to a different user
                request.session.flush()
        else:
            request.session.cycle_key()

        request.session[SESSION_KEY] = user.user_id
        request.session[BACKEND_SESSION_KEY] = 'CognitoBackend'
        request.session[HASH_SESSION_KEY] = session_auth_hash
        if hasattr(request, 'user'):
            request.user = user
        rotate_token(request)
