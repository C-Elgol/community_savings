from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from apps.communities.models import Community
import logging
from django.utils.translation import gettext_lazy as _
from apps.finance.utils.admin_mixins import AdminSeasonMixin

logger = logging.getLogger(__name__)

class AdminMemberView(AdminSeasonMixin, DetailView):
    model = Community
    template_name = 'publics/admin/members/members.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any other members-specific data here
        return context
