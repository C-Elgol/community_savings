from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.utils.translation import gettext_lazy as _
import json
import logging

from apps.communities.models import Community, Membership, MembershipApplication
from apps.global_data.enum import MembershipStatus, MembershipRole
from apps.communities.tasks.membership_tasks import (
    send_application_submitted_emails_task,
    send_application_review_result_email_task
)

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
            'verification': {
                'document_type': app.document_type,
                'document_type_display': app.get_document_type_display(),
                'document_front': app.document_front.url if app.document_front else None,
                'document_back': app.document_back.url if app.document_back else None,
                'selfie_photo': app.selfie_photo.url if app.selfie_photo else None,
            }
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
                
                # Trigger Celery task for review result email
                send_application_review_result_email_task.delay(str(app.id))
                
                return JsonResponse({'success': True, 'message': _("Application approved and member active.")})

            elif action == 'reject':
                reason = data.get('reason', '')
                if not reason:
                    return JsonResponse({'success': False, 'message': _("Rejection reason is required.")}, status=400)
                
                app.status = MembershipStatus.REJECTED
                app.rejection_reason = reason
                app.save()
                
                # Trigger Celery task for review result email
                send_application_review_result_email_task.delay(str(app.id))
                
                return JsonResponse({'success': True, 'message': _("Application rejected.")})
            
            else:
                return JsonResponse({'success': False, 'message': _("Invalid action.")}, status=400)

        except Exception as e:
            logger.error(f"Error processing application: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class ApplicationCreateAPI(View):
    def get(self, request, community_id):
        community = get_object_or_404(Community, id=community_id)
        policy = getattr(community, 'policy', None)
        user = request.user
        
        data = {
            'community_name': community.name,
            'community_code': '', # Do not pre-fill to force user input
            'registration_fee_mode': policy.registration_fee_mode if policy else 'none',
            'registration_fee_amount': str(policy.registration_fee_amount) if policy else '0.00',
            'role': MembershipRole.MEMBER,
            'role_display': MembershipRole.MEMBER.label,
            'user': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone_number': str(user.phone_number) if user.phone_number else ''
            }
        }
        return JsonResponse({'success': True, 'data': data})

    @transaction.atomic
    def post(self, request, community_id):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': _("Authentication required.")}, status=401)
            
        community = get_object_or_404(Community, id=community_id)
        
        # Check if already a member
        if Membership.objects.filter(community=community, user=request.user, is_deleted=False).exists():
            return JsonResponse({'success': False, 'message': _("You are already a member of this community.")}, status=400)
            
        # Check if already applied
        if MembershipApplication.objects.filter(community=community, user=request.user, status=MembershipStatus.PENDING).exists():
            return JsonResponse({'success': False, 'message': _("You already have a pending application for this community.")}, status=400)
            
        try:
            # Handle FormData (MultiPartParser)
            data = request.POST
            files = request.FILES
            
            # Community Code Validation
            submitted_code = data.get('community_code')
            if submitted_code != community.code:
                return JsonResponse({'success': False, 'message': _("Invalid community code. Please check and try again.")}, status=400)
            
            # Profile Updates
            user = request.user
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            phone_number = data.get('phone_number')
            
            if first_name: user.first_name = first_name
            if last_name: user.last_name = last_name
            if phone_number: user.phone_number = phone_number
            user.save()

            applied_role = MembershipRole.MEMBER
            
            policy = getattr(community, 'policy', None)
            reg_fee_required = policy.registration_fee_mode != 'none' if policy else False
            reg_fee_amount = policy.registration_fee_amount if policy else 0
            
            # Application Creation with Documents
            application = MembershipApplication.objects.create(
                community=community,
                user=user,
                applied_role=applied_role,
                status=MembershipStatus.PENDING,
                registration_fee_required=reg_fee_required,
                registration_fee_amount=reg_fee_amount,
                document_type=data.get('document_type', 'id_card'),
                document_front=files.get('document_front'),
                document_back=files.get('document_back'),
                selfie_photo=files.get('selfie_photo')
            )
            
            # Trigger Celery task for submission emails
            send_application_submitted_emails_task.delay(str(application.id))
            
            return JsonResponse({
                'success': True, 
                'message': _("Application submitted successfully. It is now pending review."),
                'application_id': str(application.id)
            })
        except Exception as e:
            logger.error(f"Error creating application: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
