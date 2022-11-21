from cognito.backend import CognitoBackend
from django.conf import settings

_cognitobackend = CognitoBackend()
SESSION_KEY = settings.SESSION_KEY

class UserMiddleware:

    def __init__(self, response):
        self.response = response

    def __call__(self, request):
        try:
            user_id = request.session[SESSION_KEY]
        except KeyError:
            user_id = None
        user = _cognitobackend.init_user_from_id(user_id)
        request.user = user
        return self.response(request)
