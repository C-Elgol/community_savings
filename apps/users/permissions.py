from apps.global_data.enum import CommunitySpaceRole

# Define functional areas for permissions
AREAS = {
    'dashboard': 'Dashboard access',
    'members': 'Member management',
    'applications': 'Membership applications',
    'loans': 'Loan management',
    'loans_approve': 'Loan approval (President/Owner specific)',
    'contributions': 'Njangi/Contributions management',
    'fines': 'Fines management',
    'expenditures': 'Expenditures management',
    'expenditures_approve': 'Expenditure approval',
    'interest_sharing': 'Interest shared management',
    'meetings': 'Meetings & Minutes',
    'reports': 'Financial reports',
    'analytics': 'Credit risk analytics',
    'logs': 'System audit logs',
    'settings': 'Community settings',
}

# Role to Area mapping
ROLE_PERMISSIONS = {
    CommunitySpaceRole.OWNER: list(AREAS.keys()),
    CommunitySpaceRole.PRESIDENT: [
        'dashboard', 'members', 'applications', 'loans', 'loans_approve',
        'expenditures', 'expenditures_approve', 'reports', 'meetings', 'analytics'
    ],
    CommunitySpaceRole.MANAGER: [
        'dashboard', 'members', 'applications', 'meetings', 'contributions'
    ],
    CommunitySpaceRole.CHAIRPERSON: [
        'dashboard', 'members', 'meetings', 'reports'
    ],
    CommunitySpaceRole.SECRETARY: [
        'dashboard', 'members', 'meetings'
    ],
    CommunitySpaceRole.TREASURER: [
        'dashboard', 'contributions', 'loans', 'expenditures', 'fines', 'interest_sharing'
    ],
    CommunitySpaceRole.AUDITOR: [
        # Auditor has read-only access to almost everything, 
        # but we handle read-only in the mixin/decorator
        'dashboard', 'members', 'applications', 'loans', 'contributions', 
        'fines', 'expenditures', 'interest_sharing', 'meetings', 'reports', 
        'analytics', 'logs'
    ],
    CommunitySpaceRole.LOAN_OFFICER: [
        'dashboard', 'loans', 'analytics'
    ],
    CommunitySpaceRole.VIEWER: [
        'dashboard', 'reports'
    ],
}

from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from apps.communities.models import CommunitySpaceMembership, Community
from apps.global_data.enum import CommunitySpaceRole

def has_area_permission(user_role, area):
    """
    Check if a given role has permission for a specific area.
    """
    if not user_role:
        return False
    
    # Superusers have all permissions
    # In the decorator we check user.is_superuser
    
    permissions = ROLE_PERMISSIONS.get(user_role, [])
    return area in permissions

from apps.finance.models import FinancialSeason

def rbac_permission_required(area):
    """
    Decorator for views that checks if the user has permission for a specific area.
    Expects community_id or season_id in view arguments.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            community_id = kwargs.get('community_id')
            season_id = kwargs.get('season_id')
            
            if not community_id:
                if season_id:
                    season = FinancialSeason.objects.filter(id=season_id).first()
                    if season:
                        community_id = season.community_id
                
                if not community_id:
                    # Try to get from post data if not in URL
                    community_id = request.POST.get('community_id')
            
            if not community_id:
                return view_func(request, *args, **kwargs)

            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            community = Community.objects.filter(id=community_id).first()
            if not community:
                return view_func(request, *args, **kwargs)
                
            space = community.community_space
            is_owner = space.owner == request.user
            
            membership = CommunitySpaceMembership.objects.filter(
                community_space=space,
                user=request.user
            ).first()
            
            role = membership.role if membership else None
            if is_owner:
                role = CommunitySpaceRole.OWNER

            if not has_area_permission(role, area):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return JsonResponse({
                        'success': False, 
                        'message': "You can't access this feature"
                    }, status=403)
                
                request.session['rbac_unauthorized'] = True
                return redirect(reverse('users:admin_dashboard', kwargs={'community_id': community_id}))

            # Auditor read-only check
            if role == CommunitySpaceRole.AUDITOR and request.method not in ('GET', 'HEAD', 'OPTIONS'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                    return JsonResponse({
                        'success': False, 
                        'message': "Auditors have read-only access."
                    }, status=403)
                
                request.session['rbac_unauthorized'] = True
                return redirect(reverse('users:admin_dashboard', kwargs={'community_id': community_id}))

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
