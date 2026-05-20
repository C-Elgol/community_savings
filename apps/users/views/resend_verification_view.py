import logging
import traceback
from typing import Any

from django.db import transaction
from django.http import HttpRequest, JsonResponse
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
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

logger = logging.getLogger(__name__)


class ResendVerificationView(TemplateView):
    """
    Handles resending of verification code for inactive accounts via AJAX.
    """
    @method_decorator(log_activity_and_errors())
    def post(self, request: HttpRequest, email: str, *args: Any, **kwargs: Any) -> JsonResponse:
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        try:
            user = User.objects.filter(email=email, is_active=False).first()
            if not user:
                return JsonResponse({'success': False, 'message': _('No inactive account found.')}, status=404)

            with transaction.atomic():
                code = get_random_string(6, allowed_chars='0123456789')
                if not isinstance(user.metadata, dict):
                    user.metadata = {}
                user.metadata["two_factor_code"] = code
                user.metadata["two_factor_code_created_at"] = timezone.now().isoformat()
                user.save()

                html_content = render_to_string(
                    "publics/emails/two_factor_email.html",
                    {"user": user, "two_factor_code": code, "site_name": "NjangiHub"}
                )

                email_message = EmailMessage(
                    subject="Your NjangiHub Verification Code",
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
                action="Resent verification code",
                module="Authentication",
                status=LogSystemStatus.SUCCESS,
            )

            return JsonResponse({
                'success': True,
                'message': _('New code sent to your email.'),
                'redirect_url': reverse('users:verify_2fa', kwargs={'email': email})
            })

        except Exception as e:
            logger.error(f"Error resending code: {e}")
            return JsonResponse({'success': False, 'message': _('An error occurred.')}, status=500)