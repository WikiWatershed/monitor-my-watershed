from django.shortcuts import redirect
from django.shortcuts import render
from django.contrib.auth import logout as django_logout
from django.conf import settings
from auth.backend import CognitoBackend
from datetime import datetime

_cognitobackend = CognitoBackend()

_SESSION_KEY = settings.SESSION_KEY
_BACKEND_SESSION_KEY = settings.BACKEND_SESSION_KEY
_HASH_SESSION_KEY = settings.HASH_SESSION_KEY

#def login_required(view, *args, **kwargs):
#    def authenicated(request, *args, **kwargs):
#        user = request.user
#        if user.is_authenticated: return view(request, *args, **kwargs)
#        else: return redirect(login)
#    return authenicated

def login(request):
    return (redirect (settings.COGNITO_SIGNIN_URL))

def logout(request):
    django_logout(request)
    return redirect('home')

def signup(request):
    return (redirect (settings.COGNITO_SIGNUP_URL))

def login_failed(request):
    """Placeholder authorization failed endpoint"""
    return render(
        request,
        'dms_ui/login_failed.html',
        {
            'title':'Login Failed',
            'year':datetime.now().year,
        }
    )

def _login_success(request):    
    """post login placeholder for more advanced rerouting - e.g. organziation specific page"""
    return redirect('home')

def oauth2_cognito(request):
    try: 
        auth_code = request.GET['code']
        user = _cognitobackend.authenticate(code=auth_code)
        _cognitobackend.login(request, user)
        return _login_success(request)
    except Exception as e:
        return redirect(login_failed)
 

