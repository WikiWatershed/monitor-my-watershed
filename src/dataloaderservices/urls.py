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

from dataloaderservices import views

urlpatterns = [
    url(r'^api/data-stream/$', views.TimeSeriesValuesApi.as_view(), name='api_post'),
    url(r'^api/csv-values/$', views.CSVDataApi.as_view(), name='csv_data_service'),
    url(r'^api/follow-site/$', views.FollowSiteApi.as_view(), name='follow_site'),
    url(r'^api/register-sensor/$', views.RegisterSensorApi.as_view(), name='register_sensor_service'),
    url(r'^api/edit-sensor/$', views.EditSensorApi.as_view(), name='edit_sensor_service'),
    url(r'^api/delete-sensor/$', views.DeleteSensorApi.as_view(), name='delete_sensor_service'),
    url(r'^api/delete-leafpack/$', views.DeleteLeafpackApi.as_view(), name='delete_leafpack_service'),
    url(r'^api/organization/$', views.OrganizationApi.as_view(), name='organization_service'),
    url(r'^api/output-variables/$', views.OutputVariablesApi.as_view(), name='output_variables_service'),
    url(r'^api/data-file-upload/(?P<registration_id>.*?)$', views.SensorDataUploadView.as_view(), name='data_file_upload'),
    url(r'^api/organizations/$', views.Organizations.as_view(), name='organizations'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
