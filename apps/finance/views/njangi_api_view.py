import json
import logging
from decimal import Decimal
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.utils.translation import gettext_lazy as _

from apps.communities.models import Membership
from apps.finance.models import FinancialSeason, ContributionCycle, NjangiRotation, NjangiBenefit
from apps.global_data.enum import CommunityFeatureType

logger = logging.getLogger(__name__)

class NjangiRotationAPI(View):
    def get(self, request, season_id):
        season = get_object_or_404(FinancialSeason, id=season_id)
        rotations = NjangiRotation.objects.filter(season=season).select_related('membership__user')
        
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
        
        # Check if already benefited
        benefit = NjangiBenefit.objects.filter(cycle=cycle).first()
        
        data = {
            'position': index,
            'beneficiary': {
                'id': rotation.membership.id,
                'full_name': rotation.membership.user.get_full_name,
                'email': rotation.membership.user.email,
            } if rotation else None,
            'is_benefited': benefit is not None,
            'benefit_details': {
                'amount': float(benefit.amount),
                'date': benefit.benefited_date.isoformat(),
                'transaction_id': benefit.transaction_id
            } if benefit else None
        }
        return JsonResponse({'success': True, 'data': data})

    @transaction.atomic
    def post(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amount = Decimal(str(data.get('amount', cycle.expected_amount)))
            
            membership = get_object_or_404(Membership, id=membership_id)
            
            if NjangiBenefit.objects.filter(cycle=cycle).exists():
                return JsonResponse({'success': False, 'message': _("This meeting already has a recorded beneficiary.")}, status=400)
            
            import uuid
            NjangiBenefit.objects.create(
                membership=membership,
                season=cycle.season,
                cycle=cycle,
                amount=amount,
                benefited_date=timezone.now().date(),
                transaction_id=f"NJ-{uuid.uuid4().hex[:8].upper()}"
            )
            
            return JsonResponse({'success': True, 'message': _("Njangi benefit recorded successfully.")})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
