# /home/siisi/atmp/users/views.py

from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib.auth.views import (
    #LoginView, 
    LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import CustomUser
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
)


class RegisterView(CreateView):
    template_name = 'users/register.html'
    form_class = CustomUserCreationForm
    #success_url = reverse_lazy('users:login')
    success_url = reverse_lazy('two_factor:login')


#class CustomLoginView(LoginView):
#    template_name = 'users/login.html'
#    authentication_form = CustomAuthenticationForm


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_2fa'] = self.request.user.totpdevice_set.filter(confirmed=True).exists()
        return context


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('users:login')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.txt'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = reverse_lazy('users:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'
