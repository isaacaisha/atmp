# /home/siisi/atmp/atmp_app/auth_serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth import get_user_model # <--- Get Django's active User model

User = get_user_model() # Get the actual User model defined in settings.AUTH_USER_MODEL


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

    class Meta:
        model = User
        fields = [
            'id', 'name', 'username', 'email', 'role',
            'password1', 'password2',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, data):
        """
        Custom validation to authenticate the user.
        This method is called after individual field validations.
        """
        if data['password1'] != data['password2']:
            raise serializers.ValidationError({'password2': _('Passwords do not match.')})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        raw_password = validated_data.pop('password1')
        user = User(**validated_data)
        user.set_password(raw_password)  # ✅ Proper Django password1 hashing
        user.save()
        return user

    def update(self, instance, validated_data):
        validated_data.pop('password2', None)
        if 'password1' in validated_data:
            raw_password = validated_data.pop('password1')
            instance.set_password(raw_password)  # ✅ Proper password1 update
        return super().update(instance, validated_data)


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    Handles validation of username/email and password.
    """
    username = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(write_only=True)
    otp_token = serializers.CharField(
        write_only=True, required=False, help_text="6-digit TOTP code if 2FA is enabled"
    )


class ProfileSerializer(serializers.ModelSerializer):
    has_2fa = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "email", "name", "username", "role", "has_2fa"]

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
