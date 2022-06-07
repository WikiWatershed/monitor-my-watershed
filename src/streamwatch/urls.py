from django.conf.urls import url

from .views import StreamWatchCreateView
#, StreamWatchDetailView, StreamWatchDeleteView, StreamWatchUpdateView, download_StreamWatch_csv

urlpatterns = [
    url(r'create/$', StreamWatchCreateView.as_view(), name='create'),
    # url(r'(?P<pk>.*?)/update/$', StreamWatchUpdateView.as_view(), name='update'),
    # url(r'(?P<pk>.*?)/delete/$', StreamWatchDeleteView.as_view(), name='delete'),
    # url(r'(?P<pk>.*?)/csv/$', download_StreamWatch_csv, name='csv_download'),
    # url(r'(?P<pk>.*?)/$', StreamWatchDetailView.as_view(), name='view'),
]
