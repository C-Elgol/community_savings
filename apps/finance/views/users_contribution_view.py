from django.views.generic import ListView
import logging
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Q
from django.contrib.auth.mixins import LoginRequiredMixin

from apps.finance.models import Contribution, FinancialSeason
from apps.communities.models import Membership
from apps.global_data.enum import ContributionStatus

logger = logging.getLogger(__name__)

class UsersContributionView(LoginRequiredMixin, ListView):
    model = Contribution
    template_name = 'publics/home/contribution/contribution.html'
    context_object_name = 'contributions'

    def get_queryset(self):
        memberships = Membership.objects.filter(user=self.request.user, is_deleted=False)
        self.active_feature = self.request.GET.get('feature_type', 'njangi')
        self.active_season_id = self.request.GET.get('season_id')

        # If no season_id provided, find the latest one for this feature
        if not self.active_season_id:
            seasons = FinancialSeason.objects.filter(
                community__memberships__in=memberships
            ).distinct()
            
            if self.active_feature == 'njangi':
                latest_season = seasons.filter(Q(feature_type='njangi') | Q(feature_type__isnull=True)).order_by('-season_date').first()
            else:
                latest_season = seasons.filter(feature_type=self.active_feature).order_by('-season_date').first()
            
            if latest_season:
                self.active_season_id = str(latest_season.id)

        queryset = Contribution.objects.filter(
            membership__in=memberships
        ).select_related(
            'cycle', 
            'membership__community', 
            'cycle__season',
            'cycle__njangi_benefit__membership__user'
        )

        if self.active_feature == 'njangi':
            queryset = queryset.filter(Q(cycle__feature_type='njangi') | Q(cycle__feature_type__isnull=True))
        else:
            queryset = queryset.filter(cycle__feature_type=self.active_feature)

        if self.active_season_id:
            queryset = queryset.filter(cycle__season_id=self.active_season_id)

        return queryset.order_by('-cycle__due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_memberships = Membership.objects.filter(user=self.request.user, is_deleted=False)
        
        # Get all features the user is participating in
        from apps.finance.views.admin_contributions_view import CONTRIBUTION_FEATURE_TYPES
        
        # We want to show Njangi + any other enabled features in the user's communities
        user_features = set(['njangi'])
        for membership in user_memberships:
            enabled = membership.community.features.filter(is_active=True).values_list('feature_type', flat=True)
            user_features.update(enabled)
        
        # Available seasons for the active feature
        seasons = FinancialSeason.objects.filter(
            community__memberships__in=user_memberships
        ).distinct()
        
        if self.active_feature == 'njangi':
            active_seasons = seasons.filter(Q(feature_type='njangi') | Q(feature_type__isnull=True))
        else:
            active_seasons = seasons.filter(feature_type=self.active_feature)

        # Totals and counts based on current filters
        all_filtered = self.get_queryset()
        
        total_contributed = all_filtered.filter(
            status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        pending_cycles_count = all_filtered.filter(status=ContributionStatus.PENDING).count()

        # Njangi beneficiaries for this season
        season_beneficiaries = []
        if self.active_feature == 'njangi' and self.active_season_id:
            from apps.finance.models import NjangiBenefit
            season_beneficiaries = NjangiBenefit.objects.filter(
                season_id=self.active_season_id
            ).select_related('cycle', 'membership__user').order_by('cycle__due_date')

        context.update({
            'available_features': sorted(list(user_features)),
            'available_seasons': active_seasons.order_by('-season_date'),
            'active_feature': self.active_feature,
            'active_feature_label': self.active_feature.replace('_', ' ').title(),
            'active_season_id': self.active_season_id,
            'season_beneficiaries': season_beneficiaries,
            'total_contributed': total_contributed,
            'pending_cycles_count': pending_cycles_count,
            'active_menu': 'contributions'
        })
        return context
