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
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.urls import reverse_lazy
from django.conf.urls.static import static

# TODO: Figure out where this is being initialized
# Removes User and Group models from admin page
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

admin.site.unregister(User)
admin.site.unregister(Group)

# BASE_URL = settings.SITE_URL[1:]
BASE_URL = ""

login_configuration = {"redirect_field_name": "next"}

logout_configuration = {"next_page": reverse_lazy("home")}

password_reset_configuration = {"post_reset_redirect": "password_reset_done"}

password_done_configuration = {"post_reset_redirect": "password_reset_complete"}

# TODO: Clean out old auth urls
# fmt: off
urlpatterns = [
    url(r"^" + BASE_URL + "admin/", admin.site.urls),
    url( r"^" + BASE_URL + "api-auth/", include("rest_framework.urls", namespace="rest_framework"),),
    url( r"^" + BASE_URL + "hydroshare/", include("hydroshare.urls", namespace="hydroshare"),),
    url(BASE_URL, include("dataloaderinterface.urls")),
    url(BASE_URL, include("dataloaderservices.urls")),
    url(BASE_URL, include("timeseries_visualization.urls")),
    url(BASE_URL, include("accounts.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# fmt: on
