import re
import logging
import traceback
from typing import Any
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.core.mail import EmailMessage, get_connection
from django.db import transaction
from django.contrib import messages
from decouple import config

from apps.users.models import User

logger = logging.getLogger(__name__)


class RegisterView(TemplateView):
    """
    Name: RegisterView
    Description: Handles user registration via AJAX form submission.
                 Uses transaction.atomic() to ensure all operations are atomic.
                 Sends a 2FA code via email and returns JSON responses.
                 Uses ToastManager for error/success messages via client-side.
    Author: ayemeleelgol@gmail.com
    """
    template_name = 'publics/auth/register.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {'error': None})

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()
        terms = request.POST.get("terms", "")

        # Fields to return in case of error
        fields = {
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'last_name': last_name,
            'email': email,
            'terms': terms == "on"
        }

        # Check if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            # ===== VALIDATIONS =====
            if not all([first_name, last_name, email, password, confirm_password]):
                error_message = _("All fields are required.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            if terms != "on":
                error_message = _("You must agree to the Terms of Service.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                error_message = _("Invalid email format.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            if len(password) < 8 or not re.search(r'\d', password) or not re.search(r'[A-Za-z]', password):
                error_message = _("Password must be at least 8 characters and contain at least one letter and one number.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            if password != confirm_password:
                error_message = _("Passwords do not match.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            if User.objects.filter(email=email).exists():
                error_message = _("A user with this email already exists.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
                messages.error(request, error_message)
                return render(request, self.template_name, fields)

            # ===== ATOMIC TRANSACTION =====
            with transaction.atomic():
                # Create the user
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False,
                    has_accepted_terms=True,
                )

                # Create user profile
                from apps.users.models import Profile
                Profile.objects.create(user=user)

                # Ensure metadata is a dictionary
                if not isinstance(user.metadata, dict):
                    user.metadata = {}

                # Generate and store 2FA code
                two_factor_code = get_random_string(6, allowed_chars='0123456789')
                user.metadata["two_factor_code"] = two_factor_code
                user.metadata["two_factor_code_created_at"] = timezone.now().isoformat()
                user.save()

                # Build 2FA email
                html_content = render_to_string(
                    template_name="publics/emails/two_factor_email.html",
                    context={
                        "user": user,
                        "two_factor_code": two_factor_code,
                        "site_name": "NjangiHub"
                    }
                )

                email_message = EmailMessage(
                    subject="Your 2-Factor Authentication Code",
                    body=html_content,
                    from_email=f"NjangiHub <{config('EMAIL_HOST_USER')}>",
                    to=[email],
                )
                email_message.content_subtype = "html"

                # Gmail SMTP settings from .env
                connection = get_connection(
                    backend="django.core.mail.backends.smtp.EmailBackend",
                    host="smtp.gmail.com",
                    port=587,
                    username=config('EMAIL_HOST_USER'),
                    password=config('EMAIL_HOST_PASSWORD'),
                    use_tls=True
                )
                email_message.connection = connection

                # Send email
                email_message.send()

            logger.info(f"✅ User registered and 2FA code sent to {email} (ID: {user.id})")
            success_message = _("Registration successful! Please check your email for the 2FA code.")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('users:verify_2fa', kwargs={'email': email})
                })
            messages.success(request, success_message)
            return redirect('users:verify_2fa', email=email)

        except Exception as e:
            trace = traceback.format_exc()
            logger.error(f"Unexpected error during registration for email {email}: {e}\n{trace}")
            error_message = _("An unexpected error occurred. Please try again later.")
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message, 'fields': fields})
            messages.error(request, error_message)
            return render(request, self.template_name, fields)


class Verify2FAView(TemplateView):
    """
    Name: Verify2FAView
    Description: Handles 2FA code verification via AJAX.
                 Activates user account and logs them in on success.
                 Returns JSON responses for AJAX requests.
    Author: ayemeleelgol@gmail.com
    """
    template_name = 'publics/auth/verify_2fa.html'

    def get(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        return render(request, self.template_name, {'email': email, 'error': None})

    def post(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> HttpResponse:
        code = request.POST.get("code", "").strip()
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                error_message = _("No user found with this email.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message})
                messages.error(request, error_message)
                return render(request, self.template_name, {'email': email})

            if not isinstance(user.metadata, dict) or "two_factor_code" not in user.metadata:
                error_message = _("Invalid or expired 2FA code. Please register again.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message})
                messages.error(request, error_message)
                return render(request, self.template_name, {'email': email})

            stored_code = user.metadata.get("two_factor_code")
            code_created_at = user.metadata.get("two_factor_code_created_at")
            if not stored_code or not code_created_at:
                error_message = _("Invalid or expired 2FA code. Please register again.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message})
                messages.error(request, error_message)
                return render(request, self.template_name, {'email': email})

            # Check if code is expired (10 minutes)
            from datetime import datetime
            created_at = datetime.fromisoformat(code_created_at)
            if (timezone.now() - created_at).total_seconds() > 600:
                error_message = _("2FA code has expired. Please register again.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message})
                messages.error(request, error_message)
                return render(request, self.template_name, {'email': email})

            if code != stored_code:
                error_message = _("Invalid 2FA code.")
                if is_ajax:
                    return JsonResponse({'success': False, 'message': error_message})
                messages.error(request, error_message)
                return render(request, self.template_name, {'email': email})

            # Activate user and clear 2FA code
            with transaction.atomic():
                user.is_active = True
                user.metadata.pop("two_factor_code", None)
                user.metadata.pop("two_factor_code_created_at", None)
                user.save()

                from django.contrib.auth import login
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            logger.info(f"✅ User {email} verified 2FA and logged in (ID: {user.id})")
            success_message = _("2FA verification successful! You are now logged in.")
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('users:login')
                })
            messages.success(request, success_message)
            return redirect('users:login')

        except Exception as e:
            trace = traceback.format_exc()
            logger.error(f"Unexpected error during 2FA verification for email {email}: {e}\n{trace}")
            error_message = _("An unexpected error occurred. Please try again later.")
            if is_ajax:
                return JsonResponse({'success': False, 'message': error_message})
            messages.error(request, error_message)
            return render(request, self.template_name, {'email': email})