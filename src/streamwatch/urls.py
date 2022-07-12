from django.conf.urls import url

from streamwatch import views

urlpatterns = [
    # url(r'create/$', StreamWatchCreateView.as_view(), name='create'),
    url(r'(?P<pk>.*?)/addsensor/$', views.StreamWatchCreateMeasurementView.as_view(), name='addsensor'),
    url(r'create/$', views.CreateView.as_view(), name='create'),
    # url(r'(?P<pk>.*?)/update/$', StreamWatchUpdateView.as_view(), name='update'),
    url(r'(?P<pk>.*?)/delete/$', views.StreamWatchDeleteView.as_view(), name='delete'),
    url(r'(?P<pk>.*?)/csv/$', views.download_StreamWatch_csv, name='csv_download'),
    url(r'(?P<pk>.*?)/$', views.StreamWatchDetailView.as_view(), name='view'),
]
