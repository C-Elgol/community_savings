from django.views.generic import TemplateView
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class CommunitySpaceView(TemplateView):
    template_name = 'publics/superadmin/community_space/community_space.html'
