from abc import ABCMeta, abstractmethod, abstractproperty
import re
import requests
from oauthlib.oauth2 import InvalidGrantError
from hs_restclient import HydroShareAuthOAuth2, HydroShareAuthBasic
from hydroshare_util.adapter import HydroShareAdapter
from . import HydroShareUtilityBaseClass, ImproperlyConfiguredError
from django.shortcuts import redirect
import logging as logger


OAUTH_ROPC = 'oauth-resource-owner-password-credentials'
OAUTH_AC = 'oauth-authorization-code'
BASIC_AUTH = 'basic'
SELF_SIGNED_CERTIFICATE = 'self-signed-certificate'


class AuthUtil(HydroShareUtilityBaseClass):
    """
    Main authentication class. Use 'AuthUtilFactory' to create instances of this class.
    """
    def __init__(self, implementation):
        self.__implementation = implementation

    @property
    def auth_type(self):
        return self.__implementation.auth_type

    def get_client(self):
        return self.__implementation.get_client()

    def get_token(self):
        return self.__implementation.get_token()

    def refresh_token(self):
        auth_type = self.auth_type
        if auth_type == OAUTH_ROPC or auth_type == OAUTH_AC:
            return self.__implementation.refresh_access_token()

    @staticmethod
    def authorize_client(request, response_type=None):
        return OAuthUtil.authorize_client(request, response_type=response_type)

    @staticmethod
    def authorize_client_callback(request):
        return OAuthUtil.authorize_client_callback(request)

    @staticmethod
    def authorize(scheme=None, username=None, password=None, token=None, hostname=None, port=None):
        return AuthUtilFactory.create(scheme=scheme, username=username, password=password, token=token,
                                      hostname=hostname, port=port)


class AuthUtilImplementor(HydroShareUtilityBaseClass):
    """Defines bridging interface for implementation classes of 'AuthUtil'"""
    __metaclass__ = ABCMeta

    @abstractproperty
    def auth_type(self):
        pass

    @abstractmethod
    def get_client(self):
        pass

    @abstractmethod
    def get_token(self):
        pass


class OAuthUtil(AuthUtilImplementor):
    """User authentication with OAuth 2.0 using the 'authorization_code' grant type"""
    _required_token_fields = ['response_type', 'access_token', 'token_type', 'expires_in', 'refresh_token', 'scope']
    _HS_BASE_URL_PROTO_WITH_PORT = '{scheme}://{hostname}:{port}/'
    _HS_BASE_URL_PROTO = '{scheme}://{hostname}/'
    _HS_API_URL_PROTO = '{base}hsapi/'
    _HS_OAUTH_URL_PROTO = '{base}o/'

    __client_id = None
    __client_secret = None
    __redirect_uri = None

    @property
    def auth_type(self):
        return self.__authorization_grant_type

    def __init__(self, use_https=True, hostname='www.hydroshare.org', client_id=None, client_secret=None,
                 redirect_uri=None, port=None, scope=None, access_token=None, refresh_token=None, expires_in=None,
                 token_type='Bearer', response_type='code', username=None, password=None):

        if client_id:
            self.__client_id = client_id

        if client_secret:
            self.__client_secret = client_secret

        if redirect_uri:
            self.__redirect_uri = redirect_uri

        if not all([self.__client_id, self.__client_secret, self.__redirect_uri]):
            raise ImproperlyConfiguredError()

        self.token_type = token_type
        self.response_type = response_type
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.scope = scope
        self.username = username
        self.password = password

        if use_https:
            self.scheme = 'https'
        else:
            self.scheme = 'http'

        if port is None:
            self.base_url = self._HS_BASE_URL_PROTO.format(scheme=self.scheme, hostname=hostname)
        else:
            self.base_url = self._HS_BASE_URL_PROTO_WITH_PORT.format(scheme=self.scheme, port=port, hostname=hostname)

        self.api_url = self._HS_API_URL_PROTO.format(base=self.base_url)
        self.oauth_url = self._HS_OAUTH_URL_PROTO.format(base=self.base_url)

        if self.username and self.password:
            self.__authorization_grant_type = OAUTH_ROPC
        else:
            self.__authorization_grant_type = OAUTH_AC

    def get_token(self):
        """
        Get the authorization token dict
        :return: a dictionary representing the oauth token
        """
        token = {
            'access_token': self.access_token,
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'refresh_token': self.refresh_token,
            'scope': self.scope
        }
        for key, value in token.iteritems():
            if value is None:
                missing_attrs = [field for field in self._required_token_fields if
                                 getattr(self, field) is None and not re.search(r'^__[a-zA-Z0-9]+__$', field)]
                if len(missing_attrs) > 0:
                    raise AttributeError("missing attributes(s) for token: {attrs}".format(attrs=missing_attrs))
        return token

    def get_client(self):  # type: () -> HydroShareAdapter
        """
        Passes authentication details to underlying HydroShare object for authorization via OAuth 2.0.
        """
        if self.auth_type == OAUTH_AC:
            token = self.get_token()
            auth = HydroShareAuthOAuth2(self.__client_id, self.__client_secret, token=token)
        elif self.auth_type == OAUTH_ROPC:
            auth = HydroShareAuthOAuth2(self.__client_id, self.__client_secret, username=self.username,
                                        password=self.password)
        else:
            raise InvalidGrantError("Invalid authorization grant type.")

        authorization_header = self.get_authorization_header()
        return HydroShareAdapter(auth=auth, default_headers=authorization_header)

    @staticmethod
    def authorize_client(request, response_type=None):
        """
        Redirects user from the client (data.envirodiy.org) to www.hydroshare.org/o/authorize/. After the user provides
        their hydroshare account credentials and authorizes the requesting client, the user is redirected back to the
        client website.
        :param request: A Django HttpRequest object
        :param response_type: (optional) a string representing the auth response type (defaults is 'code').
        :return: None
        """
        if response_type:
            auth = OAuthUtil(response_type=response_type)
        else:
            auth = OAuthUtil()

        url = auth._get_authorization_code_url(request)
        return redirect(url)

    @staticmethod
    def authorize_client_callback(request, response_type=None):  # type: (str, str) -> dict
        """
        Callback handler after a user authorizes the client (data.envirodiy.org).
        :param request: a Django HttpRequest
        :param response_type: a string representing the oauth response_type
        :return: a dictionary representing the token
        """
        if response_type:
            auth = OAuthUtil(response_type=response_type)
        else:
            auth = OAuthUtil()

        token = auth._request_access_token(request)

        return token

    def get_authorization_header(self):
        return {'Authorization': '{token_type} {access_token}'.format(token_type=self.token_type,
                                                                      access_token=self.access_token)}

    def _set_token(self, **token):
        for key, value in token.iteritems():
            if key in self.__dict__:
                setattr(self, key, value)
            else:
                logger.warning("skipped setting attribute '{attr}' on '{clsname}".format(attr=key,
                                                                                         clsname=self.classname))

    def refresh_access_token(self):
        """
        Refresh oauth token using the refresh_token
        :return: a dictionary representing the refreshed token
        """
        params = {
            'grant_type': 'refresh_token',
            'client_id': self.__client_id,
            'client_secret': self.__client_secret,
            'refresh_token': self.refresh_token
        }

        url = self._build_oauth_url('token/', params)

        response = requests.post(url)

        if response.status_code == 200:
            responseJSON = response.json()

            self.access_token = responseJSON['access_token']
            self.refresh_token = responseJSON['refresh_token']
            self.expires_in = responseJSON['expires_in']
            self.scope = responseJSON['scope']

        else:
            # TODO: better exception handling
            raise Exception("failed to refresh access token", response.json())

        return self.get_token()

    def _build_oauth_url(self, path, params=None):  # type: (str, dict) -> str
        if params is None:
            params = {}

        url_params = []
        for key, value in params.iteritems():
            url_params.append('{0}={1}'.format(key, value))

        return "{oauth_url}{path}?{params}".format(oauth_url=self.oauth_url, path=path, params="&".join(url_params))

    def _get_authorization_code_url(self, request):

        redirect_url = self._get_redirect_url(request.scheme, request.META['HTTP_HOST'])

        params = {
            'response_type': self.response_type,
            'client_id': self.__client_id,
            'redirect_uri': redirect_url
        }

        return self._build_oauth_url('authorize/', params)

    def _get_access_token_url(self, request):

        redirect_url = self._get_redirect_url(request.scheme, request.META['HTTP_HOST'])

        params = {
            'grant_type': 'authorization_code',
            'client_id': self.__client_id,
            'client_secret': self.__client_secret,
            'redirect_uri': redirect_url,
            'code': request.GET['code']
        }

        return self._build_oauth_url('token/', params)

    def _get_redirect_url(self, scheme, host):
        if scheme and host in self.__redirect_uri:
            return self.__redirect_uri

        redirect_uri = self.__redirect_uri
        if '/' == redirect_uri[0]:
            redirect_uri = redirect_uri[1:]

        return '{scheme}://{host}/{uri}'.format(scheme=scheme, host=host, uri=redirect_uri)

    def _request_access_token(self, request):
        url = self._get_access_token_url(request)

        response = requests.post(url)

        if response.status_code == 200 and 'json' in dir(response):
            return response.json()
        else:
            # TODO: Better exception handling...
            raise Exception("failed to get access token")


class BasicAuthUtil(AuthUtilImplementor):
    """User authentication using 'Basic Auth' scheme."""

    def __init__(self, username, password):
        self.username = username
        self.password = password

        self.__auth_type = BASIC_AUTH

    @property
    def auth_type(self):
        return self.__auth_type

    def get_client(self):
        auth = HydroShareAuthBasic(username=self.username, password=self.password)
        return HydroShareAdapter(auth=auth)

    def get_token(self):
        return None


class SelfSignSecurityCertAuth(AuthUtilImplementor):
    """Used to connect to a development HydroShare server that uses a self-sign security certificate"""
    def __init__(self, hostname, port=None):  # type: (str, int) -> None
        self.hostname = hostname
        self.port = port
        self.use_https = False

        self.__auth_type = SELF_SIGNED_CERTIFICATE

    @property
    def auth_type(self):
        return self.__auth_type

    def get_client(self):
        if self.port:
            return HydroShareAdapter(hostname=self.hostname, port=self.port, use_https=self.use_https)
        else:
            return HydroShareAdapter(hostname=self.hostname, verify=False)

    def get_token(self):
        return None


class AuthUtilFactory(object):
    """
    Factory class for creating instances of 'AuthUtil'.

    Example: Creating a 'AuthUtil' object using the 'basic' authentication scheme:
        hsauth = AuthUtilFactory.create(username='<your username>', password='<your password>')

    Example of creating a 'AuthUtil' object using the 'oauth' authentication scheme and client credential grant type:
        hsauth = AuthUtilFactory.create(scheme='oauth', username='<your_username>', password='<your_password>')

    Example of creating an 'AuthUtil' object using the 'auth' authentication scheme and authorization code grant type:
        token = get_token() # get_token is a stand for getting a token dictionary
        hsauth = AuthUtilFactory.create(token=token)
    """
    @staticmethod
    def create(scheme=None, username=None, password=None, token=None, hostname=None, port=None, use_https=None):
        # type: (AuthScheme, str, str, dict, str, int, bool) -> AuthUtil
        """
        Factory method creates and returns an instance of AuthUtil. The chosen scheme ('basic' or 'oauth') determines
        the background implementation. The following table shows which parameters are required for each type of
        authentication scheme.

        +----------------------------------------------------------------------------------------+
        |       scheme type      |  username  |  password  |   token   |  hostname  |    port    |
        +------------------------+---------------------------------------------------------------+
        | Basic Auth             |     X      |     X      |           |            |            |
        +------------------------+---------------------------------------------------------------+
        | OAuth with credentials |     X      |     X      |           |            |            |
        +------------------------+---------------------------------------------------------------+
        | OAuth with token       |            |            |     X     |            |            |
        +------------------------+---------------------------------------------------------------+
        | Security Certificate   |            |            |           |      X     |  optional  |
        +------------------------+---------------------------------------------------------------+

        :param scheme: The authentication scheme, either 'basic' or 'oauth'
        :param username: user's username
        :param password: user's password
        :param token: a dictionary containing values for 'access_token', 'token_type', 'refresh_token', 'expires_in',
        and 'scope'
        :param hostname: The hostname if using a self signed security certificate
        :param port: The port to connect to if trying to connect to a hydroshare development server
        :param use_https: True if using HTTPS is required, otherwise False, default is None
        """
        if token:
            # OAuth using authorization-code
            implementation = OAuthUtil(**token)

        elif scheme == 'oauth' and username and password:

            # OAuth using resource-owner-password-credentials
            implementation = OAuthUtil(username=username, password=password)

        elif scheme == 'basic' and username and password:

            # Basic auth - username and password
            implementation = BasicAuthUtil(username, password)

        elif scheme == 'self-signed-certificate' and hostname:

            # Auth using a self signed security certificate
            implementation = SelfSignSecurityCertAuth(hostname, port=port)

        else:

            raise ValueError("incorrect arguments supplied to 'AuthUtilFactory.create()' using authentication scheme \
                '{scheme}'".format(scheme=scheme if scheme else "not specified"))

        util = AuthUtil(implementation)

        if use_https is not None:
            util.use_https = use_https

        return util


__all__ = ["AuthUtil", "OAuthUtil", "BasicAuthUtil", "SelfSignSecurityCertAuth", "AuthUtilFactory"]
