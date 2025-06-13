# /home/siisi/atmp/users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    ROLE_PROMPT = [('', 'Select a role')] + CustomUser.ROLE_CHOICES[1:]
    role = forms.ChoiceField(
        choices=ROLE_PROMPT,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True,
    )

    class Meta:
        model = CustomUser
        fields = ['name', 'email', 'role', 'password1', 'password2']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Full Name',
                'class': 'form-control form-control-user',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email Address',
                'class': 'form-control form-control-user',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # style password fields
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Password',
            'class': 'form-control form-control-user',
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Repeat Password',
            'class': 'form-control form-control-user',
        })

class CustomAuthenticationForm(AuthenticationForm):
    username_field = CustomUser._meta.get_field('email')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Email',
            'class': 'form-control form-control-user',
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Password',
            'class': 'form-control form-control-user',
        })
