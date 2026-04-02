from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from apps.communities.models import Community
from apps.finance.models import FinancialSeason

class AdminSeasonMixin:
    """Enforces that a season is selected before accessing admin views."""
    
    def dispatch(self, request, *args, **kwargs):
        community_id = kwargs.get('community_id')
        active_seasons = request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if not season_id:
            community = get_object_or_404(Community, id=community_id)
            return redirect(reverse('users:community_space_welcome', kwargs={'pk': community.community_space_id}))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        
        active_seasons = self.request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if season_id:
            context['active_season'] = get_object_or_404(FinancialSeason, id=season_id)
            
        return context
