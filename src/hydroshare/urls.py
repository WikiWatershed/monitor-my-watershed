from django.conf.urls import url

from hydroshare.views import (HydroShareResourceUpdateView, HydroShareResourceCreateView, HydroShareResourceDeleteView, OAuthAuthorize, OAuthRedirect)

app_name = 'hydroshare'
urlpatterns = [
    url(r'oauth/redirect/$', OAuthRedirect.as_view(), name='oauth_redirect'),
    url(r'oauth/$', OAuthAuthorize.as_view(), name='oauth'),
    url(r'(?P<sampling_feature_code>.*)/create/$', HydroShareResourceCreateView.as_view(), name='create'),
    url(r'(?P<sampling_feature_code>.*)/update/$', HydroShareResourceUpdateView.as_view(), name='update'),
    url(r'(?P<sampling_feature_code>.*)/delete/$', HydroShareResourceDeleteView.as_view(), name='delete'),
]