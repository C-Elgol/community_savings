import json
import logging
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.utils.translation import gettext_lazy as _

from apps.communities.models import Community, Membership
from apps.finance.models import ContributionCycle, Contribution, Fine, FinancialSeason
from apps.global_data.enum import CommunityFeatureType, FineType, FineStatus, ContributionStatus

logger = logging.getLogger(__name__)

class FineEligibleMembersAPI(View):
    def get(self, request, cycle_id, fine_type):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        community = cycle.community
        
        try:
            # Get members in Njangi feature
            memberships = Membership.objects.filter(
                community=community,
                status='active',
                feature_participations__feature__feature_type=CommunityFeatureType.NJANGI,
                feature_participations__is_active=True
            ).select_related('user')
            
            if fine_type == 'late_contribution':
                # Exclude those who have PAID or PARTIAL contributions
                paid_member_ids = Contribution.objects.filter(
                    cycle=cycle,
                    status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]
                ).values_list('membership_id', flat=True)
                
                eligible = memberships.exclude(id__in=paid_member_ids)
            elif fine_type == 'absence':
                # For absence, we might show everyone or use some attendance logic 
                # but the user said "members who have not yet paid" which usually implies 
                # those expected at the meeting but haven't contributed yet.
                # However, for absence, it's typically全員 except maybe excused?
                # User request: "shows all members who hwvw not yet paid for that meeting"
                # This phrasing seems applied to the "late payments" click.
                # Let's assume for now both use the same logic of non-contributors.
                paid_member_ids = Contribution.objects.filter(
                    cycle=cycle,
                    status__in=[ContributionStatus.PAID]
                ).values_list('membership_id', flat=True)
                eligible = memberships.exclude(id__in=paid_member_ids)
            else:
                return JsonResponse({'success': False, 'message': 'Invalid fine type'}, status=400)

            members_list = [
                {
                    'id': m.id,
                    'full_name': m.user.get_full_name,
                    'email': m.user.email,
                }
                for m in eligible
            ]
            
            return JsonResponse({'success': True, 'members': members_list})
        except Exception as e:
            logger.error(f"Error fetching eligible fine members: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

class LaunchFinesAPI(View):
    @transaction.atomic
    def post(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        community = cycle.community
        policy = getattr(community, 'policy', None)
        
        if not policy:
            return JsonResponse({'success': False, 'message': _("Community policy not found.")}, status=400)
            
        try:
            data = json.loads(request.body)
            member_ids = data.get('member_ids', [])
            fine_type = data.get('fine_type')
            
            if not fine_type or not member_ids:
                return JsonResponse({'success': False, 'message': _("Missing data.")}, status=400)
                
            amount = Decimal("0.00")
            reason_prefix = ""
            
            if fine_type == 'late_contribution':
                amount = policy.late_contribution_fine_amount
                reason_prefix = _("Late Contribution")
            elif fine_type == 'absence':
                amount = policy.absence_fine_amount
                reason_prefix = _("Absence")
            else:
                return JsonResponse({'success': False, 'message': _("Invalid fine type.")}, status=400)

            if amount <= 0:
                return JsonResponse({'success': False, 'message': _("Fine amount in policy is 0. Please set it in settings.")}, status=400)

            fines_created = 0
            for mid in member_ids:
                membership = get_object_or_404(Membership, id=mid, community=community)
                
                # Link to contribution if exists
                contribution = Contribution.objects.filter(membership=membership, cycle=cycle).first()
                
                Fine.objects.create(
                    membership=membership,
                    season=cycle.season,
                    fine_type=fine_type,
                    amount=amount,
                    reason=f"{reason_prefix} - {cycle.title}",
                    issued_date=timezone.now().date(),
                    related_contribution=contribution,
                    status=FineStatus.UNPAID
                )
                fines_created += 1
                
            return JsonResponse({
                'success': True, 
                'message': _(f"Successfully issued {fines_created} fines.")
            })
        except Exception as e:
            logger.error(f"Error launching fines: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
