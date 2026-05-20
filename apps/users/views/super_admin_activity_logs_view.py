from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.log.models import ActivityLog
import logging

logger = logging.getLogger(__name__)

class SuperAdminActivityLogsView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/superadmin/activity_logs/activity_logs.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Fetch latest logs, limit to maybe 100 for performance on single page
        ctx['logs'] = ActivityLog.objects.all().order_by('-created')[:100]
        return ctx
