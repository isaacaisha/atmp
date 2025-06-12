# /home/siisi/atmp/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser

@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    """Admin for CustomUser adding role, name, and improved layout."""

    # Columns shown on the "Users" changelist page
    list_display = (
        'email', 
        'name', 
        'role', 
        'is_staff', 
        'is_active'
    )
    list_filter = (
        'role',
        'is_staff', 
        'is_active'
    )

    # Fields on the user *change* page, grouped into logical sections
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('name', 'role')}),
        (_('Permissions'), {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            )
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    # Fields on the user *add* page
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'name',
                'role',
                'password1',
                'password2',
                'is_active',
                'is_staff',
            ),
        }),
    )

    search_fields = ('email', 'name')
    ordering = ('email',)
    readonly_fields = ('last_login', 'date_joined')
