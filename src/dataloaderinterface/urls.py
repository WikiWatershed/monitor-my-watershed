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
from django.conf.urls import url, include

import dataloaderinterface.views as views
from streamwatch import views as streamwatchviews

# fmt: off
urlpatterns = [
    url(r"^$", views.HomeView.as_view(), name="home"),
    url(r"^sites/$", views.SitesListView.as_view(), name="sites_list"),
    url(r"^terms/$", views.TermsOfUseView.as_view(), name="terms_of_use"),
    url(r"^dmca/$", views.DMCAView.as_view(), name="dmca"),
    url(r"^privacy/$", views.PrivacyView.as_view(), name="privacy"),
    url(r"^subscriptions/$", views.SubscriptionsView.as_view(), name="subscriptions"),
    url(r"^subscriptions-faq/$", views.SubscriptionsFAQView.as_view(), name="subscriptions_faq"),
    url(r"^cookies/$", views.CookiePolicyView.as_view(), name="cookie_policy"),
    url(r"^status/$", views.StatusListView.as_view(), name="status"),
    url(r"^browse/$", views.BrowseSitesListView.as_view(), name="browse_sites"),
    url( r"^sites/register/$", views.SiteRegistrationView.as_view(), name="site_registration",),
    url( r"^sites/update/(?P<sampling_feature_code>.*?)/sensors/$", views.SensorListUpdateView.as_view(), name="sensors",),
    url( r"^sites/update/(?P<sampling_feature_code>.*?)/leafpacks/$", views.LeafPackListUpdateView.as_view(), name="leafpacks",),
    url( r"^sites/update/(?P<sampling_feature_code>.*?)/streamwatches/$", streamwatchviews.ListUpdateView.as_view(), name="streamwatches",),
    url( r"^sites/update/(?P<sampling_feature_code>.*)/$", views.SiteUpdateView.as_view(), name="site_update",),
    url( r"^sites/delete/(?P<sampling_feature_code>.*)/$", views.SiteDeleteView.as_view(), name="site_delete",),
    url( r"^sites/(?P<sampling_feature_code>.*)/leafpack/", include(("leafpack.urls", "leafpack"), namespace="leafpack"),),
    url( r"^sites/(?P<sampling_feature_code>.*)/streamwatch/", include(("streamwatch.urls", "streamwatch"), namespace="streamwatch"),),
    url( r"^sites/(?P<sampling_feature_code>.*)/$", views.SiteDetailView.as_view(), name="site_detail",),
    url(r"^dataloader/ajax/", views.ajax_router, name="ajax"),
]
# fmt: off
