import logging
from django.views.generic import TemplateView

from apps.users.models import User

logger = logging.getLogger(__name__)


class RegisterView(TemplateView):
    """
    Name: RegisterView
    Description: Handles user registration via AJAX form submission.
                 Uses transaction.atomic() to ensure all operations are atomic.
                 Sends a 2FA code via email and returns JSON responses.
                 Uses ToastManager for error/success messages via client-side.
                 Phone number is handled as full international format via intl-tel-input.
    Author: ayemeleelgol@gmail.com
    """
    template_name = 'publics/auth/register.html'
