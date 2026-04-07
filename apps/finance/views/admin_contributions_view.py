import logging
from django.views.generic import DetailView
from apps.communities.models import Community, Membership
from apps.global_data.enum import CommunityFeatureType

logger = logging.getLogger(__name__)


CONTRIBUTION_FEATURE_TYPES = [
    CommunityFeatureType.SAVINGS,
    CommunityFeatureType.ENTERTAINMENT,
    CommunityFeatureType.SINKING_FUND,
    CommunityFeatureType.PROJECT,
    CommunityFeatureType.EVENTS,
]


from apps.finance.utils.admin_mixins import AdminSeasonMixin

class AdminContributionsView(AdminSeasonMixin, DetailView):
    model = Community
    template_name = 'publics/admin/contributions/other_contributions.html'
    pk_url_kwarg = 'community_id'
    context_object_name = 'community'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community = self.get_object()

        # Build eligible members per feature type
        eligible = {}
        for ft in CONTRIBUTION_FEATURE_TYPES:
            eligible[ft.value] = list(
                Membership.objects.filter(
                    community=community,
                    status='active',
                    feature_participations__feature__feature_type=ft,
                    feature_participations__is_active=True
                ).select_related('user').distinct()
            )

        context['eligible_members_by_feature'] = eligible

        # Determine which features are enabled in this community
        enabled_features = list(
            community.features.filter(
                feature_type__in=[ft.value for ft in CONTRIBUTION_FEATURE_TYPES],
                is_active=True
            ).values_list('feature_type', flat=True)
        )
        context['enabled_features'] = enabled_features

        return context
