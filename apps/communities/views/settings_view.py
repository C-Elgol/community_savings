import json
import logging
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community, CommunityFeature, CommunityPolicy, CommunitySpaceMembership, Membership
from apps.global_data.enum import CommunityFeatureType, CommunitySpaceRole

logger = logging.getLogger(__name__)

from apps.finance.utils.admin_mixins import AdminSeasonMixin, CommunityRoleMixin
from apps.users.permissions import rbac_permission_required, has_area_permission
from django.utils.decorators import method_decorator
from django.utils.decorators import method_decorator
from apps.log.decorators import log_activity_and_errors

class AdminSettingsView(AdminSeasonMixin, LoginRequiredMixin, TemplateView):
    template_name = 'publics/admin/settings/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community_id = self.kwargs.get('community_id')
        community = get_object_or_404(Community, id=community_id)
        
        # Ensure policy exists
        policy, _ = CommunityPolicy.objects.get_or_create(community=community)
        
        # Get feature states
        features = community.features.all()
        feature_map = {f.feature_type: f.is_active for f in features}
        
        # Standard features to manage
        standard_features = [
            {'type': CommunityFeatureType.NJANGI, 'label': 'Njangi'},
            {'type': CommunityFeatureType.SAVINGS, 'label': 'Savings'},
            {'type': CommunityFeatureType.LOANS, 'label': 'Loans'},
            {'type': CommunityFeatureType.ENTERTAINMENT, 'label': 'Entertainment'},
            {'type': CommunityFeatureType.SINKING_FUND, 'label': 'Sinking Fund'},
            {'type': CommunityFeatureType.PROJECT, 'label': 'Project'},
            {'type': CommunityFeatureType.EVENTS, 'label': 'Events'},
        ]
        
        feature_states = []
        for sf in standard_features:
            feature_states.append({
                'type': sf['type'].value,
                'label': sf['label'],
                'is_active': feature_map.get(sf['type'].value, False)
            })

        # Get all members of this community
        community_memberships = Membership.objects.filter(
            community=community
        ).select_related('user')
        
        # Get space roles for these users
        space_membership_map = {
            m.user_id: m.role 
            for m in CommunitySpaceMembership.objects.filter(community_space=community.community_space)
        }
        
        # Include Owner if not in community memberships
        owner = community.community_space.owner
        display_members = []
        seen_user_ids = set()
        
        for m in community_memberships:
            user = m.user
            display_members.append({
                'user_id': str(user.id),
                'full_name': user.get_full_name,
                'email': user.email,
                'role': space_membership_map.get(user.id, 'None'), # Default to 'None' if no space role
                'is_owner': owner == user
            })
            seen_user_ids.add(user.id)
            
        if owner and owner.id not in seen_user_ids:
            display_members.append({
                'user_id': str(owner.id),
                'full_name': owner.get_full_name,
                'email': owner.email,
                'role': 'owner',
                'is_owner': True
            })

        context.update({
            'community': community,
            'policy': policy,
            'feature_states': feature_states,
            'display_members': display_members,
            'community_space_roles': CommunitySpaceRole.choices,
        })
        return context

@method_decorator(rbac_permission_required('settings'), name='dispatch')
class UpdateFeatureStatusAPI(LoginRequiredMixin, View):
    @method_decorator(log_activity_and_errors())
    def post(self, request, community_id):
        try:
            data = json.loads(request.body)
            feature_type = data.get('feature_type')
            is_active = data.get('is_active', False)
            
            community = get_object_or_404(Community, id=community_id)
            
            feature, created = CommunityFeature.objects.get_or_create(
                community=community,
                feature_type=feature_type
            )
            feature.is_active = is_active
            feature.save()
            
            # If disabling a feature, we might want to also deactivate participation?
            # For now, just toggling the feature itself is enough.
            
            return JsonResponse({
                'success': True,
                'message': f"Feature '{feature_type}' {'enabled' if is_active else 'disabled'} successfully."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@method_decorator(rbac_permission_required('settings'), name='dispatch')
class UpdateCommunitySettingsAPI(LoginRequiredMixin, View):
    @method_decorator(log_activity_and_errors())
    def post(self, request, community_id):
        try:
            data = json.loads(request.body)
            community = get_object_or_404(Community, id=community_id)
            
            community.name = data.get('name', community.name)
            community.description = data.get('description', community.description)
            community.currency = data.get('currency', community.currency)
            community.country = data.get('country', community.country)
            community.save()
            
            return JsonResponse({
                'success': True,
                'message': "Community settings updated successfully."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

@method_decorator(rbac_permission_required('settings'), name='dispatch')
class UpdateMemberRoleAPI(CommunityRoleMixin, LoginRequiredMixin, View):
    @method_decorator(log_activity_and_errors())
    def post(self, request, community_id):
        # Secure the API: only Owner or President can change roles
        community, space, role = self.get_community_and_roles(request, community_id)
        
        if not (role in (CommunitySpaceRole.OWNER, CommunitySpaceRole.PRESIDENT) or request.user.is_superuser):
            return JsonResponse({'success': False, 'message': "Only owners or presidents can manage roles."}, status=403)

        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            new_role = data.get('role')
            
            if not user_id or not new_role:
                return JsonResponse({'success': False, 'message': "User ID and role are required."}, status=400)
            
            if new_role == 'none':
                # Delete the space membership if it exists
                CommunitySpaceMembership.objects.filter(
                    community_space=space,
                    user_id=user_id
                ).delete()
                
                return JsonResponse({
                    'success': True,
                    'message': "Space role removed successfully."
                })

            # Use get_or_create to handle new space memberships
            membership, created = CommunitySpaceMembership.objects.get_or_create(
                community_space=space,
                user_id=user_id,
                defaults={'role': new_role}
            )
            
            if not created:
                membership.role = new_role
                membership.save()
            
            return JsonResponse({
                'success': True,
                'message': f"Role for {membership.user.get_full_name} updated to {membership.get_role_display()}."
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
