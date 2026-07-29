from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """Allows access only to Admin users or superusers."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return (
            getattr(request.user, 'role', None) == 'Admin' or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsProviderUser(permissions.BasePermission):
    """Allows access only to Provider users."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, 'role', None) == 'Provider'
