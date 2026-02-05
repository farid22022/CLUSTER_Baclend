
from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'STUDENT'
        )

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == 'SUPER_ADMIN'
        )


class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ('ADMIN', 'SUPER_ADMIN')
        )


class IsLayeredAdminForPage(BasePermission):
    """Used for content management on specific pages"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.user.role in ('SUPER_ADMIN', 'ADMIN'):
            return True

        if request.user.role != 'LAYERED_ADMIN':
            return False

        page_name = getattr(view, 'page_name', None)
        if not page_name:
            return False

        return request.user.assigned_pages.filter(name__iexact=page_name).exists()


class IsSuperAdminOnlyForSensitiveActions(BasePermission):
    """Restrict dangerous actions (promote to superadmin, assign pages, delete superadmin)"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'SUPER_ADMIN'

    def has_object_permission(self, request, view, obj):
        if not request.user.role == 'SUPER_ADMIN':
            return False
        # Prevent SUPER_ADMIN from demoting/deleting other SUPER_ADMIN (optional strict mode)
        if obj.role == 'SUPER_ADMIN' and obj != request.user:
            return False
        return True




class IsAssignedToPage(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user has access to this page (based on view's page_id)
        page_id = getattr(view, 'page_id', None)
        if not page_id:
            return False

        return page_id in request.user.assigned_pages.values_list('name', flat=True) or getattr(request.user, 'role', None) == 'SUPER_ADMIN'