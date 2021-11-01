from django.conf.urls import url
from timeseries_visualization import views

APP_URL = 'tsv'

urlpatterns = [
    url(r'^' + APP_URL + '/home/$', views.home, name='timeseries_visualization'),
]