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


class IsProvider(permissions.BasePermission): # This name is kept from original, but functionality is more "IsCreatorOrSafetyManagerOrSuperuser"
    """
    Allows full access to superusers, object-level access to the 'created_by' user
    or the 'safety_manager' user. This permission should primarily be used for
    object-level permissions where the `get_queryset` of the ViewSet might not be sufficient
    (e.g., for update/delete operations).
    """
    def has_permission(self, request, view):
        # For list and create operations, IsSuperuserOrEmployee is often sufficient.
        # This permission can act as a fallback or additional check.
        # If the view's get_queryset already filters objects based on user,
        # has_permission may simply allow authenticated users generally.
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Allow full access to superusers
        if request.user.is_superuser:
            return True
        
        # Allow if the user is the creator of the object
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # Allow if the user is the assigned safety manager for the object (e.g., DossierATMP)
        if hasattr(obj, 'safety_manager') and obj.safety_manager == request.user:
            return True
            
        return False # Deny access otherwise


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
        return request.user.role in [UserRole.JURISTE, UserRole.SAFETY_MANAGER]

# --- NEW PERMISSION CLASSES (Ensure these are exactly as below) ---
class IsRH(BasePermission):
    """
    Allows access only to superusers or users with the 'RH' role.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role == UserRole.RH

class IsQSE(BasePermission):
    """
    Allows access only to superusers or users with the 'QSE' role.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role == UserRole.QSE

class IsDirection(BasePermission):
    """
    Allows access only to superusers or users with the 'DIRECTION' role.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.role == UserRole.DIRECTION
