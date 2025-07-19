# /home/siisi/atmp/atmp_app/auth_serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser
from django_otp.plugins.otp_totp.models import TOTPDevice


class EmptySerializer(serializers.Serializer):
    pass


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=199)
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES[1:],
        error_messages={'required': _('This field is required.')}
    )
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password2': _('Passwords do not match.')})
        return data


class LoginSerializer(serializers.Serializer):
    username = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(write_only=True)
    otp_token = serializers.CharField(
        write_only=True, required=False, help_text="6-digit TOTP code if 2FA is enabled"
    )


class ProfileSerializer(serializers.ModelSerializer):
    has_2fa = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "email", "name", "role", "has_2fa"]

    def get_has_2fa(self, user):
        return bool(TOTPDevice.objects.filter(user=user, confirmed=True))


class LogoutSerializer(serializers.Serializer):
    """If you want to collect credentials on logout, add fields here."""
    # example: ask for email+password on logout
    email = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(write_only=True, label=_("Password"))

    def validate(self, data):
        # make sure the email belongs to an existing user
        try:
            user = CustomUser.objects.get(email=data['email'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": _("No user with that email.")})
        data['user_obj'] = user
        return data
