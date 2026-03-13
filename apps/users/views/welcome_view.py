from django.views.generic import TemplateView
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin
import logging

from apps.communities.models import CommunitySpace, Community, Membership, MembershipApplication

logger = logging.getLogger(__name__)

class WelcomeView(TemplateView):
    """
    Dynamic welcome page showing user's communities and available groups.
    """
    template_name = 'publics/welcome/welcome_page.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Available communities (Discovery) - Only show if not already a member
        # For authenticated users, exclude communities they are already in
        available_qs = Community.objects.all().order_by('-created')
        if user.is_authenticated:
            joined_community_ids = Membership.objects.filter(user=user).values_list('community_id', flat=True)
            available_qs = available_qs.exclude(id__in=joined_community_ids)
        
        context['available_communities'] = available_qs[:6] # Limit for the landing page
        
        if user.is_authenticated:
            # 2. My Communities (Joined)
            context['my_memberships'] = Membership.objects.filter(
                user=user, 
                status='active'
            ).select_related('community').order_by('-joined_at')
            
            # 3. Community Spaces (Directly owned or member of)
            # Fetch spaces where user is the owner
            owned_spaces = CommunitySpace.objects.filter(owner=user)
            
            # Fetch spaces where user is a member through CommunitySpaceMembership
            from apps.communities.models import CommunitySpaceMembership
            member_spaces_ids = CommunitySpaceMembership.objects.filter(user=user).values_list('community_space_id', flat=True)
            member_spaces = CommunitySpace.objects.filter(id__in=member_spaces_ids)
            
            # Combine or pass separately
            context['my_spaces'] = (owned_spaces | member_spaces).distinct()
            
            # 4. Pending Applications
            context['pending_applications'] = MembershipApplication.objects.filter(
                user=user,
                status='pending'
            ).select_related('community').order_by('-created')
            
        return context
