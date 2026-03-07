from django.views.generic import TemplateView
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class UsersContributionView(TemplateView):
    template_name = 'publics/home/contribution/contribution.html'
