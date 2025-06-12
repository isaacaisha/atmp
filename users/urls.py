# /home/siisi/atmp/users/urls.py

from django.urls import path
from .views import RegisterView, CustomLoginView, CustomLogoutView, HomeView

app_name = 'users'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
