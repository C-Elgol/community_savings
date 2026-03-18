from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.finance.models import FinancialSeason, ContributionCycle, Contribution
from apps.communities.models import Community, Membership
from apps.global_data.enum import ContributionStatus
from django.utils import timezone
import json

class SeasonAPI(View):
    def get(self, request, community_id):
        seasons = FinancialSeason.objects.filter(community_id=community_id).values('id', 'title', 'season_date', 'is_closed')
        return JsonResponse({'success': True, 'seasons': list(seasons)})

    def post(self, request, community_id):
        try:
            data = json.loads(request.body)
            community = get_object_or_404(Community, id=community_id)
            season = FinancialSeason.objects.create(
                community=community,
                title=data.get('title'),
                season_date=data.get('season_date')
            )
            return JsonResponse({'success': True, 'message': 'Season created successfully', 'season_id': str(season.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

class CycleAPI(View):
    def get(self, request, season_id):
        cycles = ContributionCycle.objects.filter(season_id=season_id).values('id', 'title', 'due_date', 'expected_amount', 'is_closed')
        return JsonResponse({'success': True, 'cycles': list(cycles)})

    def post(self, request, season_id):
        try:
            data = json.loads(request.body)
            season = get_object_or_404(FinancialSeason, id=season_id)
            cycle = ContributionCycle.objects.create(
                community=season.community,
                season=season,
                title=data.get('title'),
                due_date=data.get('due_date'),
                expected_amount=data.get('expected_amount'),
                is_special=data.get('is_special', False)
            )
            return JsonResponse({'success': True, 'message': 'Cycle created successfully', 'cycle_id': str(cycle.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

class ContributionAPI(View):
    def get(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        memberships = Membership.objects.filter(community=cycle.community, status='active')
        
        contributions = Contribution.objects.filter(cycle=cycle)
        contrib_map = {str(c.membership_id): c for c in contributions}
        
        data = []
        for m in memberships:
            c = contrib_map.get(str(m.id))
            data.append({
                'membership_id': str(m.id),
                'member_name': m.user.get_full_name,
                'expected_amount': str(cycle.expected_amount),
                'amount_paid': str(c.amount_paid) if c else '0.00',
                'status': c.status if c else ContributionStatus.PENDING,
                'paid_at': c.paid_at.isoformat() if c and c.paid_at else None,
            })
        
        return JsonResponse({'success': True, 'contributions': data})

    def post(self, request, cycle_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amount_paid = float(data.get('amount_paid', 0))
            
            cycle = get_object_or_404(ContributionCycle, id=cycle_id)
            membership = get_object_or_404(Membership, id=membership_id)
            
            contribution, created = Contribution.objects.get_or_create(
                membership=membership,
                cycle=cycle,
                defaults={'expected_amount': cycle.expected_amount}
            )
            
            contribution.amount_paid = amount_paid
            expected = float(contribution.expected_amount)
            
            if amount_paid >= expected:
                contribution.status = ContributionStatus.PAID
            elif amount_paid > 0:
                contribution.status = ContributionStatus.PARTIAL
            else:
                contribution.status = ContributionStatus.PENDING
            
            contribution.paid_at = timezone.now() if amount_paid > 0 else None
            contribution.save()
            
            return JsonResponse({'success': True, 'message': 'Contribution recorded successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
