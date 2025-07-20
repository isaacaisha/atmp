# /home/siisi/atmp/users/views.py

from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from two_factor.views import LoginView as TwoFactorLoginView
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext as _

from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

from .models import CustomUser
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
)


class RegisterView(CreateView):
    template_name = 'users/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('two_factor:login')


class CustomLoginView(TwoFactorLoginView):
    def get_form_list(self):
        form_list = super().get_form_list()
        # Override the 'auth' step form with our custom one
        form_list['auth'] = CustomAuthenticationForm
        return form_list

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        # Always include captcha in context
        if 'captcha' not in context:
            context['captcha'] = ReCaptchaField(widget=ReCaptchaV2Checkbox(
                attrs={'data-size': 'compact'}
            ))
            
        # Try to get email/username from form data (prefixed with step name)
        # form.data is a QueryDict that has all POST data, including the current step's fields
        email = form.data.get('auth-username') or form.data.get('auth-email') or ''

        if form.errors:
            print(f"Form errors: {form.errors}")
            messages.warning(
                self.request,
                _('Invalid reCAPTCHA or User email: "{email}" or Password doesn\'t exist 😝').format(email=email)
            )
        return context



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
