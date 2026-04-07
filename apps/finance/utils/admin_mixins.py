from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from apps.communities.models import Community, CommunitySpaceMembership
from apps.global_data.enum import CommunitySpaceRole
from apps.finance.models import FinancialSeason
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

class CommunityRoleMixin:
    """Mixin to handle role-based access control for community spaces."""
    
    def get_community_and_roles(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        space = community.community_space
        
        is_owner = space.owner == request.user
        membership = CommunitySpaceMembership.objects.filter(
            community_space=space,
            user=request.user
        ).first()
        
        role = membership.role if membership else None
        is_president = role == CommunitySpaceRole.PRESIDENT
        is_auditor = role == CommunitySpaceRole.AUDITOR
        
        return community, space, is_owner, is_president, is_auditor

    def check_permissions(self, request, is_owner, is_president, is_auditor):
        # Superusers always have access
        if request.user.is_superuser:
            return True

        if not (is_owner or is_president or is_auditor):
            return False
            
        if is_auditor and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return False
            
        return True

class AdminSeasonMixin(CommunityRoleMixin):
    """Enforces that a season is selected and user has proper roles."""
    
    def dispatch(self, request, *args, **kwargs):
        community_id = kwargs.get('community_id')
        community, space, is_owner, is_president, is_auditor = self.get_community_and_roles(request, community_id)
        
        if not self.check_permissions(request, is_owner, is_president, is_auditor):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                msg = "Auditor role: Read-only access." if is_auditor else "Permission denied."
                return JsonResponse({'success': False, 'message': msg}, status=403)
            raise PermissionDenied("You do not have permission to access this community.")

        active_seasons = request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if not season_id:
            return redirect(reverse('users:community_space_welcome', kwargs={'pk': space.id}))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        
        active_seasons = self.request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if season_id:
            context['active_season'] = get_object_or_404(FinancialSeason, id=season_id)
            
        return context
