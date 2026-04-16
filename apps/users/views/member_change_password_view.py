import re
import logging
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class MemberChangePasswordView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/home/profile/change_password.html'

    def post(self, request, *args, **kwargs):
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        user = request.user

        # Basic Validation
        if not all([current_password, new_password, confirm_password]):
            return JsonResponse({'status': 'error', 'message': _("All fields are required.")})

        if not user.check_password(current_password):
            return JsonResponse({'status': 'error', 'message': _("Current password is incorrect.")})

        if new_password != confirm_password:
            return JsonResponse({'status': 'error', 'message': _("New passwords do not match.")})

        # Password Strength Validation (Industry Standard - 8+ chars, upper, lower, digit, special)
        if len(new_password) < 8:
            return JsonResponse({'status': 'error', 'message': _("Password must be at least 8 characters long.")})
        
        if not re.search(r'[A-Z]', new_password):
            return JsonResponse({'status': 'error', 'message': _("Password must contain at least one uppercase letter.")})
        
        if not re.search(r'[a-z]', new_password):
            return JsonResponse({'status': 'error', 'message': _("Password must contain at least one lowercase letter.")})
            
        if not re.search(r'\d', new_password):
            return JsonResponse({'status': 'error', 'message': _("Password must contain at least one digit.")})
            
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            return JsonResponse({'status': 'error', 'message': _("Password must contain at least one special character.")})

        if current_password == new_password:
            return JsonResponse({'status': 'error', 'message': _("New password cannot be the same as the current password.")})

        try:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            logger.info(f"✅ Password changed successfully for user {user.email}")
            return JsonResponse({'status': 'success', 'message': _("Password changed successfully!")})
        except Exception as e:
            logger.error(f"❌ Error changing password for user {user.email}: {e}")
            return JsonResponse({'status': 'error', 'message': _("An unexpected error occurred. Please try again.")})
