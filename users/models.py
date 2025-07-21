# /home/siisi/atmp/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django_otp import user_has_device
from django.utils.translation import gettext as _


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)  # Set default role for superuser
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrator'
    JURISTE = 'JURISTE', 'Jurist'
    RH = 'RH', 'Resources Humaines'
    MANAGER = 'MANAGER', 'Manager'
    SAFETY_MANAGER = 'SAFETY_MANAGER', 'Safety Manager'
    QSE = 'QS', 'Quality, Safety, Environment'
    DIRECTION = 'DR', 'Direction'
    EMPLOYEE = 'EMPLOYEE', 'Employee'


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True, null=True, verbose_name=_('Email'))
    name  = models.CharField(max_length=199, null=True, verbose_name=_('Name'))
    role  = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.EMPLOYEE,
        verbose_name=_('Role'),
        help_text=_('Defines the user role in the system')
    )

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def is_verified(self):
        return user_has_device(self)

    def __str__(self):
        return f"{self.name} ({self.email}, {self.get_role_display()})"

    @classmethod
    @property
    def ROLE_CHOICES(cls):
        return UserRole.choices
        
    @property
    def is_safety_manager(self):
        return self.role == UserRole.SAFETY_MANAGER

    @property
    def is_jurist(self):
        return self.role == UserRole.JURISTE

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN or self.is_superuser
    