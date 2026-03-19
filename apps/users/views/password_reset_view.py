import re
import logging
import traceback
from typing import Any
from datetime import datetime

from django.contrib import messages
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage, get_connection
from django.views.generic import TemplateView
from decouple import config

from apps.users.models import User
from apps.log.models import ActivityLog, FunctionalErrorLog, LogSystemStatus

logger = logging.getLogger(__name__)


class PasswordResetRequestView(TemplateView):
    """
    Handles password reset request: sends 2FA-style code to email.
    """
    template_name = 'publics/auth/password_reset_request.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {'error': None})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        email = request.POST.get("email", "").strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        fields = {'email': email}

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                msg = _("No account found with this email.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg, 'fields': fields})
                messages.error(request, msg)
                return render(request, self.template_name, fields)

            if not user.is_active:
                msg = _("Account is inactive. Please activate first.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg, 'fields': fields})
                messages.error(request, msg)
                return render(request, self.template_name, fields)

            with transaction.atomic():
                code = get_random_string(6, allowed_chars='0123456789')
                if not isinstance(user.metadata, dict):
                    user.metadata = {}
                user.metadata["reset_code"] = code
                user.metadata["reset_code_created_at"] = timezone.now().isoformat()
                user.save()

                html_content = render_to_string(
                    "publics/emails/two_factor_email.html",
                    {
                        "user": user,
                        "two_factor_code": code,
                        "site_name": "NjangiHub",
                        "is_reset": True,  # To customize email for reset
                    }
                )

                email_message = EmailMessage(
                    subject="Your NjangiHub Password Reset Code",
                    body=html_content,
                    from_email=f"NjangiHub <{config('EMAIL_HOST_USER')}>",
                    to=[email],
                )
                email_message.content_subtype = "html"

                connection = get_connection(
                    host="smtp.gmail.com",
                    port=587,
                    username=config("EMAIL_HOST_USER"),
                    password=config("EMAIL_HOST_PASSWORD"),
                    use_tls=True,
                )
                email_message.connection = connection
                email_message.send()

            ActivityLog.log_action(
                user=user,
                action="Password reset code sent",
                module="Authentication",
                status=LogSystemStatus.SUCCESS,
            )

            success_message = _("Reset code sent to your email.")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('users:password_reset_verify', kwargs={'email': email})
                })
            messages.success(request, success_message)
            return redirect('users:password_reset_verify', email=email)

        except Exception as e:
            logger.error(f"Error sending reset code: {e}")
            msg = _("An error occurred. Please try again.")
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return render(request, self.template_name, {'email': email})


class PasswordResetVerifyView(TemplateView):
    """
    Verifies the reset code.
    """
    template_name = 'publics/auth/password_reset_verify.html'

    def get(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {'email': email, 'error': None})

    def post(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        code = request.POST.get("code", "").strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                msg = _("No user found.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            stored_code = user.metadata.get("reset_code")
            created_at_str = user.metadata.get("reset_code_created_at")
            if not stored_code or not created_at_str:
                msg = _("Invalid or expired code.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            created_at = datetime.fromisoformat(created_at_str)
            if (timezone.now() - created_at).total_seconds() > 600:
                msg = _("Code expired.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            if code != stored_code:
                msg = _("Invalid code.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            # Clear code after verification
            with transaction.atomic():
                user.metadata.pop("reset_code", None)
                user.metadata.pop("reset_code_created_at", None)
                user.save()

            success_message = _("Code verified. Set your new password.")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('users:password_reset', kwargs={'email': email})
                })
            messages.success(request, success_message)
            return redirect('users:password_reset', email=email)

        except Exception as e:
            logger.error(f"Error verifying reset code: {e}")
            msg = _("An error occurred. Please try again.")
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return render(request, self.template_name, {'email': email})


class PasswordResetView(TemplateView):
    """
    Sets the new password after code verification.
    """
    template_name = 'publics/auth/password_reset.html'

    def get(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {'email': email, 'error': None})

    def post(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            if password != confirm_password:
                msg = _("Passwords do not match.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            if len(password) < 8 or not re.search(r'\d', password) or not re.search(r'[A-Za-z]', password):
                msg = _("Password must be at least 8 characters with letters and numbers.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            user = User.objects.filter(email=email).first()
            if not user:
                msg = _("No user found.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': msg})
                messages.error(request, msg)
                return render(request, self.template_name, {'email': email})

            with transaction.atomic():
                user.set_password(password)
                user.save()

            ActivityLog.log_action(
                user=user,
                action="Password reset",
                module="Authentication",
                status=LogSystemStatus.SUCCESS,
            )

            success_message = _("Password reset successful. Please login.")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('users:login')
                })
            messages.success(request, success_message)
            return redirect('users:login')

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            msg = _("An error occurred. Please try again.")
            if is_ajax:
                return JsonResponse({'success': False, 'message': msg})
            messages.error(request, msg)
            return render(request, self.template_name, {'email': email})