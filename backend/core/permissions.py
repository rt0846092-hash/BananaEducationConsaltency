"""
Permission classes live here rather than in views.py.

settings.py names PasswordIsSet in DEFAULT_PERMISSION_CLASSES, so Django
imports this module while REST Framework is still starting up. views.py pulls
in generics and viewsets, which import REST Framework right back — a circular
import that fails at boot. This module imports almost nothing, so the cycle
never forms.
"""

from rest_framework.permissions import BasePermission


class PasswordIsSet(BasePermission):
    """Blocks every signed-in endpoint until a temporary password is replaced.

    Enforced on the server rather than by hiding a screen, so someone who skips
    the form and calls the API directly gets nowhere either.
    """

    message = "Set your own password before continuing."

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and user.must_change_password:
            return False
        return True


class IsAdmin(BasePermission):
    """Owner only. Checked here, not in the interface — hiding a button in
    React hides nothing, since anyone can call the endpoint directly."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.is_admin and not user.must_change_password
        )