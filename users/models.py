# /home/siisi/atmp/users/models.py

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext as _

# Create your models here.

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('safety_manager', 'Safety Manager'),
        ('admin', 'Administrator'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='employee',
        help_text=_('Defines if user is an employee, a safety manager, or admin.')
    )

    # Remove username field
    username = None

    name = models.CharField(max_length=199, null=True, verbose_name=_('Name'))
    email = models.EmailField(unique=True, null=True, verbose_name=_('Email'))
    # Use email as the unique identifier for login
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    # Link the custom manager to the CustomUser model
    objects = UserManager()

    def __str__(self):
        return f"{self.name} ({self.email}, ({self.role})"

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    