from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from apps.communities.models import Membership
from apps.finance.models import FinancialSeason, LoanProduct
import logging
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class MemberLoanView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/home/loans/loan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Assuming we can determine the community from the user's active membership
        # For simplicity, we take the first active membership. In a multi-community setup, 
        # this might need more logic (e.g. from session or URL).
        membership = Membership.objects.filter(user=self.request.user, status='active').first()
        if membership:
            context['membership'] = membership
            context['community'] = membership.community
            context['active_season'] = FinancialSeason.objects.filter(
                community=membership.community, 
                is_closed=False
            ).first()
            context['loan_products'] = LoanProduct.objects.filter(
                community=membership.community, 
                is_active=True
            )
        return context
