from django.conf.urls import url
from timeseries_visualization import views

APP_URL = 'tsv'

urlpatterns = [
    url(r'^' + APP_URL + '/(?P<sampling_feature_code>.*)/(?P<result_id>.*)/$', views.tsv),
    url(r'^' + APP_URL + '/(?P<sampling_feature_code>.*)/$', views.tsv),
    url(r'^' + APP_URL + '/$', views.tsv, name='timeseries_visualization'),
]