import json
import logging
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.communities.models import Community, CommunityFeature, CommunityPolicy
from apps.global_data.enum import CommunityFeatureType

logger = logging.getLogger(__name__)

class AdminSettingsView(LoginRequiredMixin, TemplateView):
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
        ]
        
        feature_states = []
        for sf in standard_features:
            feature_states.append({
                'type': sf['type'].value,
                'label': sf['label'],
                'is_active': feature_map.get(sf['type'].value, False)
            })

        context.update({
            'community': community,
            'policy': policy,
            'feature_states': feature_states,
        })
        return context

class UpdateFeatureStatusAPI(LoginRequiredMixin, View):
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

class UpdateCommunitySettingsAPI(LoginRequiredMixin, View):
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
