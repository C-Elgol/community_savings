from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import CommunitySpace, Community
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class SuperAdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/superadmin/super_admin_dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        User = get_user_model()
        
        ctx.update({
            "space_count": CommunitySpace.objects.count(),
            "user_count": User.objects.count(),
            "community_count": Community.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
        })
        return ctx
