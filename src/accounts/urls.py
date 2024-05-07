from django.urls import path
import accounts.views as views

urlpatterns = [
    path('login/oauth2_cognito/', views.oauth2_cognito, name="oauth2_cognito"),
    path('login/', views.login, name='login'),
    path('account/', views.account, name='user_account'),
    path('update_account/', views.update_account, name='user_account_update'),
    path('login_failed/', views.login_failed, name='login_failed'),
    path('signup/', views.signup, name='user_registration'),
    path('logout/', views.logout, name='logout'),
    path('reset/', views.reset_password, name='reset'),
]