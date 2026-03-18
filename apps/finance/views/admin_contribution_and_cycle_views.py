from django.views.generic import DetailView
from apps.communities.models import Community
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class AdminContributionAndCycleView(DetailView):
    model = Community
    template_name = 'publics/admin/contributions/contributions.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'
