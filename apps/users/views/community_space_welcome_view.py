from django.views.generic import DetailView
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import CommunitySpace, Community
from apps.global_data.enum import CommunityType, RegistrationFeeMode, ContributionFrequency

class CommunitySpaceWelcomeView(LoginRequiredMixin, DetailView):
    """
    Shows communities belonging to a specific Community Space.
    """
    model = CommunitySpace
    template_name = 'publics/welcome/space_welcome_page.html'
    context_object_name = 'space'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        space = self.get_object()
        
        # Communities within this space
        communities = space.communities.all().order_by('-created')
        
        # Filtering support
        q = self.request.GET.get('q', '').strip()
        if q:
            communities = communities.filter(Q(name__icontains=q) | Q(code__icontains=q))
            
        ctx.update({
            'communities': communities,
            'community_types': CommunityType.choices,
            'registration_fee_modes': RegistrationFeeMode.choices,
            'contribution_frequencies': ContributionFrequency.choices,
            'search_query': q,
        })
        return ctx
