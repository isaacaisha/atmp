# /home/siisi/atmp/users/urls.py

from django.urls import path
from . import views
from two_factor.views import LoginView

app_name = 'users'

urlpatterns = [
    #path('login/',        views.CustomLoginView.as_view(),        name='login'),
    path('account/login/', LoginView.as_view(),                    name='login'),
    #path('account/login/', views.CustomLoginView.as_view(),        name='login'),
    path('logout/',        views.CustomLogoutView.as_view(),       name='logout'),
    path('profile/',       views.ProfileView.as_view(),            name='profile'),
    path('register/',      views.RegisterView.as_view(),           name='register'),

    path('password-reset/',
         views.CustomPasswordResetView.as_view(),
         name='password_reset'),
    path('password-reset/done/',
         views.CustomPasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         views.CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('reset/done/',
         views.CustomPasswordResetCompleteView.as_view(),
         name='password_reset_complete'),
]
