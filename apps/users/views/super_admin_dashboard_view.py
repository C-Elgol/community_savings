from django.views.generic import TemplateView
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class SuperAdminDashboardView(TemplateView):
    template_name = 'publics/superadmin/super_admin_dashboard.html'
