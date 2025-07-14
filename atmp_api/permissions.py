# /home/siisi/atmp/atmp_api/permissions.py

from rest_framework import permissions


class IsProvider(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'employee'
    
    def has_object_permission(self, request, view, obj):
        return obj.provider == request.user
