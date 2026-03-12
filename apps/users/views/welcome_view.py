from django.views.generic import TemplateView
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class WelcomeView(TemplateView):
    """
    Welcome view for new users after registration.
    """
    template_name = 'publics/welcome/welcome_page.html'
