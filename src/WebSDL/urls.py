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
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.conf.urls.static import static

from accounts.views import UserRegistrationView, UserUpdateView, logout_view
import auth

#BASE_URL = settings.SITE_URL[1:]
BASE_URL = ''

login_configuration = {
    'redirect_field_name': 'next'
}

logout_configuration = {
    'next_page': reverse_lazy('home')
}

password_reset_configuration = {
    'post_reset_redirect': 'password_reset_done'
}

password_done_configuration = {
    'post_reset_redirect': 'password_reset_complete'
}

urlpatterns = [
    url(r'^' + BASE_URL + 'password-reset/$', auth_views.PasswordResetView.as_view(), password_reset_configuration, name='password_reset'),
    url(r'^' + BASE_URL + 'password-reset/done/$', auth_views.PasswordChangeView.as_view(), name='password_reset_done'),
    url(r'^' + BASE_URL + 'password-reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', auth_views.PasswordResetConfirmView.as_view(), password_done_configuration, name='password_reset_confirm'),
    url(r'^' + BASE_URL + 'password-reset/completed/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    url(r'^' + BASE_URL + 'admin/', admin.site.urls),
    ##url(r'^' + BASE_URL + 'login/$', auth_views.LoginView.as_view(), login_configuration, name='login'),
    ##url(r'^' + BASE_URL + 'logout/$', logout_view, name='logout'),
    url(r'^' + BASE_URL + 'register/$', auth.views.signup, name='user_registration'),
    url(r'^' + BASE_URL + 'account/$', UserUpdateView.as_view(), name='user_account'),
    url(r'^' + BASE_URL + 'api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^' + BASE_URL + 'hydroshare/', include('hydroshare.urls', namespace='hydroshare')),
    url(BASE_URL, include('dataloaderinterface.urls')),
    url(BASE_URL, include('dataloaderservices.urls')),
    url(BASE_URL, include('timeseries_visualization.urls')),
    url(BASE_URL, include('auth.urls')),
] + static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)

# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns = [
#         url(r'^__debug__/', include(debug_toolbar.urls)),
#     ] + urlpatterns