from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _
import json
import logging

from apps.communities.models import Community, Membership, MembershipApplication
from apps.global_data.enum import MembershipStatus

logger = logging.getLogger(__name__)

class ApplicationListAPI(View):
    def get(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        applications = MembershipApplication.objects.filter(
            community=community, 
            status=MembershipStatus.PENDING,
            is_deleted=False
        ).select_related('user').order_by('-created')
        
        data = []
        for app in applications:
            data.append({
                'id': str(app.id),
                'full_name': app.user.get_full_name or app.user.fullname or _("No Name"),
                'email': app.user.email,
                'phone_number': str(app.user.phone_number) if app.user.phone_number else '',
                'applied_role': app.applied_role,
                'applied_role_display': app.get_applied_role_display(),
                'registration_fee_required': app.registration_fee_required,
                'registration_fee_amount': str(app.registration_fee_amount),
                'created_at': app.created.strftime('%Y-%m-%d %H:%M'),
            })
            
        return JsonResponse({'success': True, 'applications': data})

class ApplicationDetailAPI(View):
    def get(self, request, application_id):
        app = get_object_or_404(MembershipApplication, id=application_id)
        u = app.user
        
        data = {
            'id': str(app.id),
            'first_name': u.first_name,
            'last_name': u.last_name,
            'email': u.email,
            'phone_number': str(u.phone_number) if u.phone_number else '',
            'applied_role': app.applied_role,
            'applied_role_display': app.get_applied_role_display(),
            'registration_fee_required': app.registration_fee_required,
            'registration_fee_amount': str(app.registration_fee_amount),
            'registration_fee_paid': app.registration_fee_paid,
            'created_at': app.created.strftime('%Y-%m-%d %H:%M'),
        }
        return JsonResponse({'success': True, 'application': data})

class ApplicationProcessAPI(View):
    @transaction.atomic
    def post(self, request, application_id):
        app = get_object_or_404(MembershipApplication, id=application_id)
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST

            action = data.get('action') # 'approve' or 'reject'
            
            if action == 'approve':
                # Update application status
                app.status = MembershipStatus.APPROVED
                app.approved_by = request.user if request.user.is_authenticated else None
                app.approved_at = timezone.now()
                app.save()

                # Create Membership
                # We need to decide on a member_code and position or leave blank
                Membership.objects.create(
                    community=app.community,
                    user=app.user,
                    role=app.applied_role,
                    status=MembershipStatus.ACTIVE,
                    joined_at=timezone.now().date(),
                    application=app
                )
                
                return JsonResponse({'success': True, 'message': _("Application approved and member active.")})

            elif action == 'reject':
                reason = data.get('reason', '')
                if not reason:
                    return JsonResponse({'success': False, 'message': _("Rejection reason is required.")}, status=400)
                
                app.status = MembershipStatus.REJECTED
                app.rejection_reason = reason
                app.save()
                
                return JsonResponse({'success': True, 'message': _("Application rejected.")})
            
            else:
                return JsonResponse({'success': False, 'message': _("Invalid action.")}, status=400)

        except Exception as e:
            logger.error(f"Error processing application: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
