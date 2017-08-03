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

from dataloaderinterface.views import DevicesListView, DeviceDetailView, SiteRegistrationView,\
    HomeView, BrowseSitesListView, SiteUpdateView, SiteDeleteView

urlpatterns = [
    url(r'^$', HomeView.as_view(), name='home'),
    url(r'^sites/$', DevicesListView.as_view(), name='sites_list'),
    url(r'^sites/browse/$', BrowseSitesListView.as_view(), name='browse_sites'),
    url(r'^sites/register/$', SiteRegistrationView.as_view(), name='site_registration'),
    url(r'^sites/update/(?P<slug>[-_\w]+)/$', SiteUpdateView.as_view(), name='site_update'),
    url(r'^sites/delete/(?P<slug>[-_\w]+)/$', SiteDeleteView.as_view(), name='site_delete'),
    url(r'^sites/(?P<slug>[-_\w]+)/$', DeviceDetailView.as_view(), name='site_detail'),

]
