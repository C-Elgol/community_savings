import logging
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
