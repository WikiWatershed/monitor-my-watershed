from django.conf.urls import url

from .views import LeafPackCreateView, LeafPackDetailView, LeafPackDeleteView, LeafPackUpdateView, download_leafpack_csv

urlpatterns = [
    url(r'create/$', LeafPackCreateView.as_view(), name='create'),
    url(r'(?P<pk>.*?)/update/$', LeafPackUpdateView.as_view(), name='update'),
    url(r'(?P<pk>.*?)/delete/$', LeafPackDeleteView.as_view(), name='delete'),
    url(r'(?P<pk>.*?)/csv/$', download_leafpack_csv, name='csv_download'),
    url(r'(?P<pk>.*?)/$', LeafPackDetailView.as_view(), name='view'),
    #url(r'delete/$', LeafPackDeleteView.as_view(), name='delete'),
]
