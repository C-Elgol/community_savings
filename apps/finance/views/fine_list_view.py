from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404

from apps.communities.models import Community
from apps.finance.utils.admin_mixins import AdminSeasonMixin

class AdminFineListView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/fines/fines.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        context['community'] = get_object_or_404(Community, id=community_id)
        return context
