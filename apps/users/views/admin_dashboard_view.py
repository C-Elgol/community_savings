from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from apps.communities.models import Community
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class AdminDashboardView(DetailView):
    model = Community
    template_name = 'publics/admin/admin_dashboard.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any other dashboard-specific data here
        return context
