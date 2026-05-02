import json
import logging
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator

from apps.communities.models import Membership
from apps.finance.models import FinancialSeason, ContributionCycle, NjangiRotation, NjangiBenefit, Expenditure, Transaction
from apps.global_data.enum import CommunityFeatureType, ExpenditureStatus
from apps.users.permissions import rbac_permission_required

logger = logging.getLogger(__name__)

class NjangiRotationAPI(View):
    def get(self, request, season_id):
        season = get_object_or_404(FinancialSeason, id=season_id)
        # Hide members who already benefited in this season
        benefited_ids = NjangiBenefit.objects.filter(season=season).values_list('membership_id', flat=True)
        rotations = NjangiRotation.objects.filter(season=season).exclude(
            membership_id__in=benefited_ids
        ).select_related('membership__user')
        
        data = [
            {
                'id': r.id,
                'membership_id': r.membership.id,
                'full_name': r.membership.user.get_full_name,
                'position': r.position
            }
            for r in rotations
        ]
        return JsonResponse({'success': True, 'rotations': data})

    def post(self, request, season_id):
        season = get_object_or_404(FinancialSeason, id=season_id)
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            position = data.get('position')
            
            membership = get_object_or_404(Membership, id=membership_id, community=season.community)
            
            # Check eligibility
            if not membership.has_feature(CommunityFeatureType.NJANGI):
                return JsonResponse({'success': False, 'message': _("Member is not enrolled in Njangi.")}, status=400)
            
            # Check if position already taken
            if NjangiRotation.objects.filter(season=season, position=position).exists():
                return JsonResponse({'success': False, 'message': _(f"Position {position} is already taken.")}, status=400)
                
            NjangiRotation.objects.create(
                season=season,
                membership=membership,
                position=position
            )
            return JsonResponse({'success': True, 'message': _("Beneficiary added to rotation.")})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    def delete(self, request, rotation_id):
        rotation = get_object_or_404(NjangiRotation, id=rotation_id)
        rotation.delete()
        return JsonResponse({'success': True, 'message': _("Beneficiary removed from rotation.")})

@method_decorator(rbac_permission_required('contributions'), name='dispatch')
class NjangiMeetingBeneficiaryAPI(View):
    def get(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        season = cycle.season
        
        # Determine position based on cycle index (ordered by due_date)
        # Using list() to get index in memory
        cycles = list(ContributionCycle.objects.filter(season=season, is_special=False).order_by('due_date'))
        try:
            index = cycles.index(cycle) + 1
        except ValueError:
            # Maybe it's special?
            return JsonResponse({'success': False, 'message': _("Cycle not found in regular rotation.")}, status=404)
            
        rotation = NjangiRotation.objects.filter(season=season, position=index).select_related('membership__user').first()
        
        benefits = NjangiBenefit.objects.filter(cycle=cycle).select_related('membership__user')
        
        data = {
            'position': index,
            'beneficiary_suggested': {
                'id': rotation.membership.id,
                'full_name': rotation.membership.user.get_full_name,
                'email': rotation.membership.user.email,
            } if rotation else None,
            'is_benefited': benefits.exists(),
            'beneficiaries': [
                {
                    'id': b.membership.id,
                    'full_name': b.membership.user.get_full_name,
                    'amount': float(b.amount),
                    'date': b.benefited_date.isoformat(),
                    'transaction_id': b.transaction_id,
                    'comment': b.comment,
                    'signature': b.signature
                }
                for b in benefits
            ]
        }
        return JsonResponse({'success': True, 'data': data})

    @transaction.atomic
    def post(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amount = Decimal(str(data.get('amount', cycle.expected_amount)))
            comment = data.get('comment', '')
            signature = data.get('signature', '')
            
            membership = get_object_or_404(Membership, id=membership_id)
            
            # We allow multiple beneficiaries per cycle now.
            # But we might want to check if THIS member already benefited in THIS cycle.
            if NjangiBenefit.objects.filter(cycle=cycle, membership=membership).exists():
                return JsonResponse({'success': False, 'message': _("This member has already benefited in this meeting.")}, status=400)
            
            import uuid
            benefit = NjangiBenefit.objects.create(
                membership=membership,
                season=cycle.season,
                cycle=cycle,
                amount=amount,
                comment=comment,
                signature=signature,
                benefited_date=timezone.now().date(),
                transaction_id=f"NJ-{uuid.uuid4().hex[:8].upper()}"
            )
            
            # Create an Expenditure to record the outflow for the community
            Expenditure.objects.create(
                community=cycle.community,
                season=cycle.season,
                source_fund=CommunityFeatureType.NJANGI,
                amount=amount,
                expenditure_date=timezone.now().date(),
                description=f"Njangi benefit payout to {membership.user.get_full_name} for cycle {cycle.title}",
                signature=signature,
                status=ExpenditureStatus.POSTED,
                created_by=request.user
            )

            # Create a Transaction for the member's personal history
            Transaction.objects.create(
                membership=membership,
                amount=amount,
                transaction_type='njangi_benefit',
                reference=benefit.transaction_id,
                description=f"Received Njangi benefit for cycle {cycle.title}"
            )
            
            return JsonResponse({'success': True, 'message': _("Njangi benefit recorded successfully.")})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
