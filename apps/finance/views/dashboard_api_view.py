from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404

from apps.communities.models import Community
from apps.finance.services.dashboard_service import DashboardService


class DashboardAPI(View):
    """Returns the full dashboard payload for a community."""

    def get(self, request, community_id):
        get_object_or_404(Community, id=community_id)
        
        # Get active season from session
        active_seasons = request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        service = DashboardService(community_id, season_id=season_id)
        return JsonResponse({'success': True, **service.full_summary()})
