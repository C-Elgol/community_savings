import logging
from django.views.generic import DetailView
from apps.finance.models import FinancialSeason
from apps.communities.models import Community, Membership
from apps.global_data.enum import CommunityFeatureType

logger = logging.getLogger(__name__)

class AdminContributionAndCycleView(DetailView):
    model = Community
    template_name = 'publics/admin/contributions/contributions.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['eligible_members'] = Membership.objects.filter(
            community=self.get_object(),
            status='active',
            feature_participations__feature__feature_type=CommunityFeatureType.NJANGI,
            feature_participations__is_active=True
        ).select_related('user').distinct()
        return context
