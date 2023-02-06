from django.urls import path
import accounts.views as views

urlpatterns = [

    path('login/oauth2_cognito/', views.oauth2_cognito, name="oauth2_cognito"),
    path('login/', views.login, name='login'),
    #FIXME: this should point to a location where user can update page
    path('account/', views.account, name='user_account'),
    path('login_failed/', views.login_failed, name='login_failed'),
    path('signup/', views.signup, name='signup'),
    #FIXME: this should point to a registration form - possibly how the user gets affiliated with a site
    path('signup/', views.signup, name='user_registration'),
    path('logout/', views.logout, name='logout'),
    ]
