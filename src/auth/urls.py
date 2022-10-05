from django.urls import path
import auth.views as views

urlpatterns = [

    path('login/oauth2_cognito/', views.oauth2_cognito, name="oauth2_cognito"),
    path('login/', views.login, name='login'),
    path('login_failed/', views.login_failed, name='login_failed'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    ]
