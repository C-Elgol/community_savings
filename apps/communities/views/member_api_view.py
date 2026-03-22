from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _
import json
import logging

from apps.communities.models import Community, Membership
from apps.users.models import User
from apps.global_data.enum import MembershipRole, MembershipStatus

logger = logging.getLogger(__name__)

class MemberListAPI(View):
    def get(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        memberships = Membership.objects.filter(community=community, is_deleted=False).select_related('user').prefetch_related('feature_participations__feature').order_by('-created')
        
        data = []
        for m in memberships:
            data.append({
                'id': str(m.id),
                'full_name': m.user.get_full_name or m.user.fullname or _("No Name"),
                'email': m.user.email,
                'member_code': m.member_code,
                'position': m.position,
                'role': m.role,
                'role_display': dict(MembershipRole.choices).get(m.role, m.role),
                'status': m.status,
                'status_display': dict(MembershipStatus.choices).get(m.status, m.status),
                'joined_at': m.joined_at.strftime('%Y-%m-%d') if m.joined_at else '',
                'features': list(m.feature_participations.filter(is_active=True).values_list('feature__feature_type', flat=True))
            })
            
        return JsonResponse({'success': True, 'members': data})

class MemberDetailAPI(View):
    def get(self, request, member_id):
        m = get_object_or_404(Membership, id=member_id)
        u = m.user
        
        data = {
            'id': str(m.id),
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'phone_number': str(u.phone_number) if u.phone_number else '',
            'member_code': m.member_code,
            'position': m.position,
            'role': m.role,
            'status': m.status,
            'joined_at': m.joined_at.strftime('%Y-%m-%d') if m.joined_at else '',
        }
        return JsonResponse({'success': True, 'member': data})

class MemberCreateAPI(View):
    @transaction.atomic
    def post(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        
        # In a real app, we'd use a form or serializer. 
        # Here we follow the user's request for manual validation and AJAX.
        try:
            # Handle both JSON and Form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            email = data.get('email')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')
            phone_number = data.get('phone_number')
            member_code = data.get('member_code', '')
            position = data.get('position', '')
            role = data.get('role', MembershipRole.MEMBER)
            joined_at = data.get('joined_at') or timezone.now().date()

            if not email:
                return JsonResponse({'success': False, 'message': _("Email is required.")}, status=400)

            # Check if user exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                }
            )

            # Check if already a member
            if Membership.objects.filter(community=community, user=user, is_deleted=False).exists():
                return JsonResponse({'success': False, 'message': _("User is already a member of this community.")}, status=400)

            # Create membership
            membership = Membership.objects.create(
                community=community,
                user=user,
                role=role,
                status=MembershipStatus.ACTIVE,
                joined_at=joined_at,
                member_code=member_code,
                position=position
            )

            return JsonResponse({
                'success': True, 
                'message': _("Member added successfully."),
                'member_id': str(membership.id)
            })

        except Exception as e:
            logger.error(f"Error creating member: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class MemberUpdateAPI(View):
    @transaction.atomic
    def post(self, request, member_id):
        m = get_object_or_404(Membership, id=member_id)
        u = m.user
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            u.first_name = data.get('first_name', u.first_name)
            u.last_name = data.get('last_name', u.last_name)
            u.phone_number = data.get('phone_number', u.phone_number)
            u.save()

            m.member_code = data.get('member_code', m.member_code)
            m.position = data.get('position', m.position)
            m.role = data.get('role', m.role)
            m.status = data.get('status', m.status)
            if data.get('joined_at'):
                m.joined_at = data.get('joined_at')
            m.save()

            return JsonResponse({'success': True, 'message': _("Member updated successfully.")})

        except Exception as e:
            logger.error(f"Error updating member: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class MemberDeleteAPI(View):
    def post(self, request, member_id):
        m = get_object_or_404(Membership, id=member_id)
        m.soft_delete()
        return JsonResponse({'success': True, 'message': _("Member removed successfully.")})

class EligibleFeatureMemberAPI(View):
    def get(self, request, community_id, feature_type):
        community = get_object_or_404(Community, id=community_id)
        # Members of this community who are NOT in the feature_type
        # or whose participation is not active
        members = Membership.objects.filter(
            community=community, 
            is_deleted=False
        ).exclude(
            feature_participations__feature__feature_type=feature_type,
            feature_participations__is_active=True
        ).select_related('user')
        
        data = [{
            'id': str(m.id),
            'full_name': m.user.get_full_name or m.user.fullname or _("No Name"),
            'email': m.user.email,
        } for m in members]
        
        return JsonResponse({'success': True, 'members': data})

class AddMemberToFeatureAPI(View):
    @transaction.atomic
    def post(self, request, community_id, feature_type):
        community = get_object_or_404(Community, id=community_id)
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                
            member_ids = data.get('member_ids', [])
            
            if not member_ids:
                return JsonResponse({'success': False, 'message': _("No members selected.")}, status=400)
                
            memberships = Membership.objects.filter(id__in=member_ids, community=community)
            
            added_count = 0
            for m in memberships:
                m.add_to_feature(feature_type)
                added_count += 1
                
            return JsonResponse({
                'success': True, 
                'message': _(f"Successfully added {added_count} members to {feature_type}.")
            })
        except Exception as e:
            logger.error(f"Error adding members to feature: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
