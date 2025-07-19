# /home/siisi/atmp/atmp_app/permissions.py

from rest_framework import permissions


class IsProvider(permissions.BasePermission):
    def has_permission(self, request, view):
        """Allow creation if superuser or employee"""
        return bool(
            request.user.is_superuser or 
            (request.user.is_authenticated and request.user.role == 'employee')
        )
    
    def has_object_permission(self, request, view, obj):
        """Allow access if superuser or owner"""
        return bool(
            request.user.is_superuser or 
            obj.provider == request.user
        )
        