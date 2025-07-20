# /home/siisi/atmp/atmp_app/mixins.py
"""
ATMP Permission System Flow:

1. LoginRequiredMixin (Django built-in)
   - Ensures user is authenticated
   - Always use as the FIRST mixin in view inheritance

2. Role-Specific Mixins (Custom)
   - ProviderOrSuperuserMixin: Employees + Superusers
     • Use for views where both roles need equal access
     • Example: Incident creation, updates
     
   - EmployeeRequiredMixin: Strictly employees only
     • Use when superusers should NOT have access
     • Example: Special employee-only reports
     
   - SafetyManagerMixin: Strictly safety managers
     • Use for safety manager dashboards/actions

3. View get_queryset() (Final filtering)
   - Applies object-level permissions
   - Filters queryset based on user role:
     • Superusers: See all records
     • Employees: See only their own incidents
     • Safety Managers: See assigned incidents
"""

from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin

from users.models import UserRole


class ProviderOrSuperuserMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Allows both employees and superusers"""
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role == UserRole.EMPLOYEE


class EmployeeRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Strictly for employees only (no superuser access)"""
    def test_func(self):
        return self.request.user.role == UserRole.EMPLOYEE


class SafetyManagerMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only for safety managers (superusers get access by default)"""
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == UserRole.SAFETY_MANAGER
