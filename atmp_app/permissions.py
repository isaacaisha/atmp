# /home/siisi/atmp/atmp_app/permissions.py

from rest_framework import permissions
from rest_framework.permissions import BasePermission
from users.models import UserRole


class IsSuperuserOrEmployee(BasePermission):
    """
    Allows access only to superusers or employees for declaration creation.
    """
    def has_permission(self, request, view):
        return bool(
            request.user.is_superuser or 
            (request.user.is_authenticated and request.user.role == UserRole.EMPLOYEE)
        )


class IsProvider(permissions.BasePermission):
    """
    Allows full access to superusers, object-level access to owners.
    """
    def has_permission(self, request, view):
        # Allow list/create if superuser or employee
        if request.method in permissions.SAFE_METHODS + ('POST',):
            return bool(
                request.user.is_superuser or 
                (request.user.is_authenticated and request.user.role == UserRole.EMPLOYEE)
            )
        return True
    
    def has_object_permission(self, request, view, obj):
        # Allow full access to superusers or object owners
        return bool(
            request.user.is_superuser or 
            obj.provider == request.user
        )


class IsSafetyManager(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        return request.user.is_authenticated and request.user.role == UserRole.SAFETY_MANAGER


class IsJurist(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role in [UserRole.JURIST, UserRole.SAFETY_MANAGER]
