
from rest_framework import permissions

class IsBarberOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == "barber"
    
    
    

class IsAdminOrBarber(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user.is_authenticated and
            request.user.role in ["admin", "barber"]
        )


class IsProviderUser(permissions.BasePermission):
    """Only allows provider users to access"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "Provider"
