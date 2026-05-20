import logging
import traceback
from typing import Any
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

logger = logging.getLogger(__name__)
User = get_user_model()

class SuperAdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only superadmins can access these views."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('users:dashboard')
        return super().handle_no_permission()

class SuperAdminUserManagementView(LoginRequiredMixin, SuperAdminRequiredMixin, TemplateView):
    """
    View to list all users in the system.
    """
    template_name = 'publics/superadmin/user_management/user_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch all users who are not soft-deleted
        # Using all_objects.filter(is_deleted=False) to be explicit
        users = User.objects.all().order_by('-date_joined')
        context['users'] = users
        return context

class AdminUserCreateView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to create a new user manually.
    """
    @method_decorator(log_activity_and_errors(action="Create User", module="User Management"))
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip() or None
        password = request.POST.get('password', '').strip()
        is_staff = request.POST.get('is_staff') == 'on'
        is_admin = request.POST.get('is_admin') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'

        if not email or not password:
            return JsonResponse({'success': False, 'message': _("Email and password are required.")}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': _("A user with this email already exists.")}, status=400)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone_number,
                    is_staff=is_staff,
                    is_admin=is_admin,
                    is_superuser=is_superuser
                )
                user.is_active = True
                user.save()
                from apps.users.models import Profile
                Profile.objects.create(user=user)
                
            return JsonResponse({'success': True, 'message': _("User created successfully.")})
        except Exception as e:
            logger.error(f"Error creating user: {e}\n{traceback.format_exc()}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class AdminUserUpdateView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to update an existing user's basic information.
    """
    @method_decorator(log_activity_and_errors(action="Update User", module="User Management"))
    def post(self, request: HttpRequest, pk: str, *args: Any, **kwargs: Any) -> HttpResponse:
        user = get_object_or_404(User, id=pk)
        
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        phone_number = request.POST.get('phone_number', '').strip() or None
        user.phone_number = phone_number
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_admin = request.POST.get('is_admin') == 'on'
        user.is_superuser = request.POST.get('is_superuser') == 'on'
        
        try:
            user.save()
            return JsonResponse({'success': True, 'message': _("User updated successfully.")})
        except Exception as e:
            logger.error(f"Error updating user {pk}: {e}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class AdminUserToggleStatusView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to toggle a user's active status.
    """
    @method_decorator(log_activity_and_errors(action="Toggle User Status", module="User Management"))
    def post(self, request: HttpRequest, pk: str, *args: Any, **kwargs: Any) -> HttpResponse:
        user = get_object_or_404(User, id=pk)
        user.is_active = not user.is_active
        user.save()
        status_str = _("activated") if user.is_active else _("deactivated")
        return JsonResponse({
            'success': True, 
            'message': _("User {status} successfully.").format(status=status_str),
            'is_active': user.is_active
        })

class AdminUserDeleteView(LoginRequiredMixin, SuperAdminRequiredMixin, View):
    """
    View to soft delete a user.
    """
    @method_decorator(log_activity_and_errors(action="Delete User", module="User Management"))
    def post(self, request: HttpRequest, pk: str, *args: Any, **kwargs: Any) -> HttpResponse:
        user = get_object_or_404(User, id=pk)
        user.soft_delete()
        return JsonResponse({'success': True, 'message': _("User soft-deleted successfully.")})
