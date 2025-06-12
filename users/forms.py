# /home/siisi/atmp/users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        # include any extra fields you want on signup
        fields = ['email', 'name', 'role', 'password1', 'password2']


class CustomAuthenticationForm(AuthenticationForm):
    # by default, AuthenticationForm uses 'username'; we want 'email'
    username_field = CustomUser._meta.get_field('email')
