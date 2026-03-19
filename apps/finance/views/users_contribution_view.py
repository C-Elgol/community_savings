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
        # Get all memberships for the current user
        memberships = Membership.objects.filter(user=self.request.user, is_deleted=False)
        # Get all contributions for these memberships
        return Contribution.objects.filter(
            membership__in=memberships
        ).select_related('cycle', 'membership__community', 'cycle__season').order_by('-cycle__due_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_memberships = Membership.objects.filter(user=self.request.user, is_deleted=False)
        
        # Better way for counts and sums
        all_contribs = Contribution.objects.filter(membership__in=user_memberships)
        
        total_contributed = all_contribs.filter(status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        # This season's total
        active_seasons = FinancialSeason.objects.filter(is_closed=False)
        this_season_contributed = all_contribs.filter(
            cycle__season__in=active_seasons,
            status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]
        ).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        
        pending_cycles_count = all_contribs.filter(status=ContributionStatus.PENDING).count()

        context.update({
            'total_contributed': total_contributed,
            'this_season_contributed': this_season_contributed,
            'pending_cycles_count': pending_cycles_count,
            'active_menu': 'contributions'
        })
        return context
