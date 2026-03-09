import logging
import traceback
from typing import Any

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView

from apps.users.models import User
from apps.log.models import ActivityLog, FunctionalErrorLog, LogSystemStatus

logger = logging.getLogger(__name__)


class LoginView(TemplateView):
    """
    Name: LoginView
    Description: Handles user login via AJAX form submission.
                 Authenticates users and ensures they are active.
                 Returns JSON responses for AJAX requests.
                 Supports next URL redirection.
    Author: ayemeleelgol@gmail.com
    """
    template_name = 'publics/auth/login.html'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        next_url = request.GET.get("next", "")  # <-- capture ?next=/path/
        return render(
            request,
            self.template_name,
            {"error": None, "email": "", "show_resend": False, "next": next_url},
        )

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()
        remember_me = request.POST.get("remember_me", "")
        next_url = request.POST.get("next", "").strip()  # <-- capture next from form

        # Fields to return in case of error
        fields = {"email": email}
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        try:
            if not all([email, password]):
                error_message = _("Email and password are required.")
                FunctionalErrorLog.log_error(
                    user=None,
                    error_type="ValidationError",
                    error_message=error_message,
                    function_or_view="LoginView.post",
                    input_data=f"email={email}, password={'*' * len(password)}",
                    context="Missing email or password in login attempt",
                    metadata={"ip_address": request.META.get("REMOTE_ADDR")},
                )
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": error_message,
                            "fields": fields,
                            "show_resend": False,
                        }
                    )
                messages.error(request, error_message)
                return render(
                    request,
                    self.template_name,
                    {"email": email, "show_resend": False, "next": next_url},
                )

            # Check if user exists
            user = User.objects.filter(email=email).first()
            if not user:
                error_message = _("Invalid email or password.")
                FunctionalErrorLog.log_error(
                    user=None,
                    error_type="AuthenticationError",
                    error_message=error_message,
                    function_or_view="LoginView.post",
                    input_data=f"email={email}, password={'*' * len(password)}",
                    context="User not found",
                    metadata={"ip_address": request.META.get("REMOTE_ADDR")},
                )
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": error_message,
                            "fields": fields,
                            "show_resend": False,
                        }
                    )
                messages.error(request, error_message)
                return render(
                    request,
                    self.template_name,
                    {"email": email, "show_resend": False, "next": next_url},
                )

            # Account inactive
            if not user.is_active:
                error_message = _(
                    "Your account is not activated. Please verify your email or resend a verification code."
                )
                FunctionalErrorLog.log_error(
                    user=user,
                    error_type="AccountInactiveError",
                    error_message=error_message,
                    function_or_view="LoginView.post",
                    input_data=f"email={email}, password={'*' * len(password)}",
                    context="User account is inactive",
                    metadata={"ip_address": request.META.get("REMOTE_ADDR")},
                )
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": error_message,
                            "fields": fields,
                            "show_resend": True,
                        }
                    )
                messages.error(request, error_message)
                return render(
                    request,
                    self.template_name,
                    {"email": email, "show_resend": True, "next": next_url},
                )

            # Authenticate user
            user = authenticate(request, email=email, password=password)
            if user is None:
                error_message = _("Invalid email or password.")
                FunctionalErrorLog.log_error(
                    user=None,
                    error_type="AuthenticationError",
                    error_message=error_message,
                    function_or_view="LoginView.post",
                    input_data=f"email={email}, password={'*' * len(password)}",
                    context="Authentication failed",
                    metadata={"ip_address": request.META.get("REMOTE_ADDR")},
                )
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": error_message,
                            "fields": fields,
                            "show_resend": False,
                        }
                    )
                messages.error(request, error_message)
                return render(
                    request,
                    self.template_name,
                    {"email": email, "show_resend": False, "next": next_url},
                )

            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            if remember_me != "on":
                request.session.set_expiry(0)

            ActivityLog.log_action(
                user=user,
                action="User logged in",
                module="Authentication",
                status=LogSystemStatus.SUCCESS,
                details=f"User {email} logged in successfully",
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                metadata={"ip_address": request.META.get("REMOTE_ADDR")},
            )

            logger.info(f"✅ User {email} logged in successfully (ID: {user.id})")
            success_message = _("Login successful! Welcome back.")

            # ✅ Safe redirect handling
            redirect_url = reverse("users:home")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                redirect_url = next_url

            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "redirect_url": redirect_url,
                    }
                )

            messages.success(request, success_message)
            return redirect(redirect_url)

        except Exception as e:
            trace = traceback.format_exc()
            FunctionalErrorLog.log_error(
                user=None,
                error_type=type(e).__name__,
                error_message=str(e),
                function_or_view="LoginView.post",
                input_data=f"email={email}, password={'*' * len(password)}",
                context="Unexpected error during login",
                traceback=trace,
                metadata={"ip_address": request.META.get("REMOTE_ADDR")},
            )
            logger.error(f"Unexpected error during login for email {email}: {e}\n{trace}")
            error_message = _("An unexpected error occurred. Please try again later.")
            if is_ajax:
                return JsonResponse(
                    {
                        "success": False,
                        "message": error_message,
                        "fields": fields,
                        "show_resend": False,
                    }
                )
            messages.error(request, error_message)
            return render(
                request,
                self.template_name,
                {"email": email, "show_resend": False, "next": next_url},
            )