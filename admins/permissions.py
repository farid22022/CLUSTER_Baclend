# from rest_framework.permissions import BasePermission

# class IsSuperAdmin(BasePermission):
#     def has_permission(self, request, view):
#         return request.user.role == 'SUPER_ADMIN'

# class IsAdminOrSuperAdmin(BasePermission):
#     def has_permission(self, request, view):
#         return request.user.role in ['ADMIN', 'SUPER_ADMIN']

# class IsAssignedToPage(BasePermission):
#     def has_permission(self, request, view):
#         # Check if user has access to this page (based on view's page_id)
#         page_id = view.page_id if hasattr(view, 'page_id') else None
#         if not page_id:
#             return False
#         return page_id in request.user.assigned_pages.values_list('name', flat=True) or request.user.role == 'SUPER_ADMIN'
from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        # Only allow authenticated users
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'role', None) == 'SUPER_ADMIN'


class IsAdminOrSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        # Only allow authenticated users
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'role', None) in ['ADMIN', 'SUPER_ADMIN']


class IsAssignedToPage(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user has access to this page (based on view's page_id)
        page_id = getattr(view, 'page_id', None)
        if not page_id:
            return False

        return page_id in request.user.assigned_pages.values_list('name', flat=True) or getattr(request.user, 'role', None) == 'SUPER_ADMIN'
