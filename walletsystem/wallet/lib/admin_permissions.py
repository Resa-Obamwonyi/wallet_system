from rest_framework import permissions
from ..models import User


class IsUserAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user

        try:
            user_instance = User.objects.get(email=user)
        except:
            return False

        if user_instance.is_admin or user_instance.is_superadmin:
            return True
        return False
