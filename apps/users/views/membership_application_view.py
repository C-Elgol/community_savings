from django.views.generic import DetailView
from django.shortcuts import get_object_or_404
from apps.communities.models import Community
import logging
from apps.finance.utils.admin_mixins import AdminSeasonMixin
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

logger = logging.getLogger(__name__)

class MembershipApplicationView(AdminSeasonMixin, DetailView):
    model = Community
    template_name = 'publics/admin/member_application/member_application.html'
    required_area = 'applications'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    @method_decorator(log_activity_and_errors(action="Viewed Membership Application", module="Communities"))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any other application-specific data here
        return context
