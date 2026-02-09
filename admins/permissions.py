from rest_framework.permissions import BasePermission, SAFE_METHODS
from .models import SystemSetting


class IsAuthenticatedStudent(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        current_role = request.user.current_role
        return current_role is not None and current_role.name.upper() == 'STUDENT'


class IsCurrentPresident(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_current_president


class IsPresidentOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        role = request.user.current_role
        if not role:
            return False
        return role.is_president or 'admin' in role.name.lower()


class HasPagePermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        page_name = getattr(view, 'page_name', None)
        if not page_name:
            return True
        return request.user.current_permissions.filter(name__iexact=page_name).exists()


class CanModifyCurrentYearContent(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        current_year = SystemSetting.get_current_year()
        obj_year = getattr(obj, 'year', None)
        return obj_year == current_year if obj_year is not None else True


class IsPresidentOnlyForDangerousActions(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_current_president

    def has_object_permission(self, request, view, obj):
        if not request.user.is_current_president:
            return False
        # Extra protection: can't modify other presidents
        if hasattr(obj, 'role') and obj.role and obj.role.is_president:
            return obj == request.user
        return True