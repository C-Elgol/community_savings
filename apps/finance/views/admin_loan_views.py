from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class AdminLoanApplicationView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loan_applications/loan_applications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.communities.models import Community
        context['community'] = Community.objects.get(id=self.kwargs['community_id'])
        return context

class AdminLoanListView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loans/loans.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.communities.models import Community
        context['community'] = Community.objects.get(id=self.kwargs['community_id'])
        return context

class AdminLoanProductView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/loan_applications/loan_products.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.communities.models import Community
        context['community'] = Community.objects.get(id=self.kwargs['community_id'])
        return context
