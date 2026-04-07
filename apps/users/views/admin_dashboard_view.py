from django.views.generic import DetailView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from apps.communities.models import Community
from apps.finance.models import FinancialSeason
from apps.finance.services.dashboard_service import DashboardService
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

from apps.finance.utils.admin_mixins import AdminSeasonMixin

class AdminDashboardView(AdminSeasonMixin, DetailView):
    model = Community
    template_name = 'publics/admin/admin_dashboard.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any other dashboard-specific data here
        return context
