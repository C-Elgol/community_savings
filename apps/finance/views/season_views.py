from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.finance.models import FinancialSeason
import json
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

class SetActiveSeasonView(View):
    @method_decorator(log_activity_and_errors())
    def post(self, request):
        try:
            data = json.loads(request.body)
            community_id = data.get('community_id')
            season_id = data.get('season_id')
            
            if not community_id or not season_id:
                return JsonResponse({'success': False, 'message': 'Missing community_id or season_id'}, status=400)
            
            # Verify the season belongs to the community
            season = get_object_or_404(FinancialSeason, id=season_id, community_id=community_id)
            
            # Store in session
            # We use a dict to store active seasons for different communities
            active_seasons = request.session.get('active_seasons', {})
            active_seasons[str(community_id)] = str(season_id)
            request.session['active_seasons'] = active_seasons
            
            return JsonResponse({
                'success': True, 
                'message': f'Active season set to {season.title or season.season_date}',
                'season_id': str(season.id)
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
