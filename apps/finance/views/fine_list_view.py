from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community

class AdminFineListView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/fines/fines.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        context['community'] = Community.objects.get(id=community_id)
        return context
