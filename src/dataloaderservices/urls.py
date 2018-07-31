"""WebSDL URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from dataloaderservices.views import TimeSeriesValuesApi, OrganizationApi, FollowSiteApi, \
    CSVDataApi, OutputVariablesApi, RegisterSensorApi, EditSensorApi, DeleteSensorApi, DeleteLeafpackApi, \
    SensorDataUploadView

urlpatterns = [
    url(r'^api/data-stream/$', TimeSeriesValuesApi.as_view(), name='api_post'),
    url(r'^api/csv-values/$', CSVDataApi.as_view(), name='csv_data_service'),
    url(r'^api/follow-site/$', FollowSiteApi.as_view(), name='follow_site'),
    url(r'^api/register-sensor/$', RegisterSensorApi.as_view(), name='register_sensor_service'),
    url(r'^api/edit-sensor/$', EditSensorApi.as_view(), name='edit_sensor_service'),
    url(r'^api/delete-sensor/$', DeleteSensorApi.as_view(), name='delete_sensor_service'),
    url(r'^api/delete-leafpack/$', DeleteLeafpackApi.as_view(), name='delete_leafpack_service'),
    url(r'^api/organization/$', OrganizationApi.as_view(), name='organization_service'),
    url(r'^api/output-variables/$', OutputVariablesApi.as_view(), name='output_variables_service'),
    url(r'^api/data-file-upload/(?P<registration_id>.*?)$', SensorDataUploadView.as_view(), name='data_file_upload')
]

urlpatterns = format_suffix_patterns(urlpatterns)
