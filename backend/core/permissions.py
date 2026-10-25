"""Role helpers and DRF permission classes.

Every authorization decision lives on the backend. The React app only hides buttons for usability.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


def is_admin(user):
    return bool(user and user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser))


def is_agent(user):
    return bool(user and user.is_authenticated and user.role == 'AGENT' and not user.is_superuser)


def is_support_staff(user):
    return is_admin(user) or is_agent(user)


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin(request.user)


class IsSupportStaff(BasePermission):
    def has_permission(self, request, view):
        return is_support_staff(request.user)


class IsAdminOrReadOnly(BasePermission):
    """Any signed-in user may read; only administrators may write."""
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        return request.method in SAFE_METHODS or is_admin(user)
