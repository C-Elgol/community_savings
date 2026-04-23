from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from apps.communities.models import Community, CommunitySpaceMembership
from apps.global_data.enum import CommunitySpaceRole
from apps.finance.models import FinancialSeason
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

from apps.users.permissions import has_area_permission, ROLE_PERMISSIONS

class CommunityRoleMixin:
    """Mixin to handle role-based access control for community spaces."""
    
    def get_community_and_roles(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        space = community.community_space
        
        # Check if user is the direct owner of the space
        is_owner = space.owner == request.user
        
        # Get membership in the community space
        membership = CommunitySpaceMembership.objects.filter(
            community_space=space,
            user=request.user
        ).first()
        
        role = membership.role if membership else None
        if is_owner:
            role = CommunitySpaceRole.OWNER

        return community, space, role

    def check_permissions(self, request, role, area=None):
        # Superusers always have access
        if request.user.is_superuser:
            return True

        if not role:
            return False
            
        # If an area is specified, check granular permission
        if area:
            if not has_area_permission(role, area):
                return False
        
        # Auditor role restriction (Read-only)
        if role == CommunitySpaceRole.AUDITOR and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            return False
            
        return True

class AdminSeasonMixin(CommunityRoleMixin):
    """Enforces that a season is selected and user has proper roles."""
    required_feature = None
    required_area = None # The functional area being accessed
    
    def dispatch(self, request, *args, **kwargs):
        community_id = kwargs.get('community_id')
        community, space, role = self.get_community_and_roles(request, community_id)
        
        # Check permissions
        if not self.check_permissions(request, role, area=self.required_area):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                msg = "You don't have permission to perform this action."
                return JsonResponse({'success': False, 'message': msg}, status=403)
            
            # Set a session flag for the toast notification
            request.session['rbac_unauthorized'] = True
            return redirect(reverse('users:admin_dashboard', kwargs={'community_id': community_id}))

        # 🔥 Enforce Feature Flag
        if self.required_feature:
            if not community.features.filter(feature_type=self.required_feature, is_active=True).exists():
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': f"The '{self.required_feature}' feature is disabled for this community."}, status=403)
                raise PermissionDenied(f"The '{self.required_feature}' feature is disabled for this community.")

        active_seasons = request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if not season_id:
            return redirect(reverse('users:community_space_welcome', kwargs={'pk': space.id}))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        community = get_object_or_404(Community, id=community_id)
        
        # Get roles for context
        _, _, role = self.get_community_and_roles(self.request, community_id)
        context['user_role'] = role
        context['user_permissions'] = ROLE_PERMISSIONS.get(role, []) if role else []

        # Clear unauthorized flag if present
        if self.request.session.get('rbac_unauthorized'):
            context['show_rbac_toast'] = True
            del self.request.session['rbac_unauthorized']

        active_seasons = self.request.session.get('active_seasons', {})
        season_id = active_seasons.get(str(community_id))
        
        if season_id:
            context['active_season'] = get_object_or_404(FinancialSeason, id=season_id)
        
        # Determine which features are enabled in this community
        context['enabled_features'] = list(
            community.features.filter(is_active=True).values_list('feature_type', flat=True)
        )
            
        return context
