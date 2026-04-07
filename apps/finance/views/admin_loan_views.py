from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community
from apps.global_data.enum import CommunityFeatureType
from apps.finance.utils.admin_mixins import AdminSeasonMixin


class AdminLoanApplicationView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loan_applications/loan_applications.html'
    required_feature = CommunityFeatureType.LOANS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['community'] = get_object_or_404(Community, id=self.kwargs['community_id'])
        return context

class AdminLoanListView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loans/loans.html'
    required_feature = CommunityFeatureType.LOANS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['community'] = get_object_or_404(Community, id=self.kwargs['community_id'])
        return context

class AdminLoanProductView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loan_applications/loan_products.html'
    required_feature = CommunityFeatureType.LOANS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['community'] = get_object_or_404(Community, id=self.kwargs['community_id'])
        return context
