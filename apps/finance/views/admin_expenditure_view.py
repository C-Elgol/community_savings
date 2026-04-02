from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community


class AdminExpenditureView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/expenditures/expenditure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['community'] = Community.objects.get(id=self.kwargs['community_id'])
        return context
