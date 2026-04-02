from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
import json

from apps.finance.models import Expenditure, Contribution, FinancialSeason
from apps.communities.models import Community
from apps.global_data.enum import CommunityFeatureType


SPENDABLE_FUNDS = [
    CommunityFeatureType.ENTERTAINMENT,
    CommunityFeatureType.PROJECT,
    CommunityFeatureType.SINKING_FUND,
    CommunityFeatureType.EVENTS,
    CommunityFeatureType.SAVINGS,
]


def _get_community_fund_balance(community_id, source_fund):
    """Compute available balance: SUM(contributions) - SUM(expenditures) for this fund and community."""
    total_in = Contribution.objects.filter(
        cycle__community_id=community_id,
        feature_type=source_fund,
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')

    total_out = Expenditure.objects.filter(
        community_id=community_id,
        source_fund=source_fund,
        status='posted',
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    return total_in - total_out


class ExpenditureBalanceAPI(View):
    """Returns available balance for each spendable fund in a community."""
    def get(self, request, community_id):
        get_object_or_404(Community, id=community_id)
        balances = {}
        for fund in SPENDABLE_FUNDS:
            balances[fund.value] = str(_get_community_fund_balance(community_id, fund.value))
        return JsonResponse({'success': True, 'balances': balances})


class ExpenditureAPI(View):
    def get(self, request, community_id):
        source_fund = request.GET.get('source_fund', '')
        expenditures = Expenditure.objects.filter(community_id=community_id)
        if source_fund:
            expenditures = expenditures.filter(source_fund=source_fund)

        expenditures = expenditures.select_related('created_by', 'season').order_by('-expenditure_date')

        # Build summary stats by fund
        stats = {}
        for fund in SPENDABLE_FUNDS:
            stats[fund.value] = str(
                Expenditure.objects.filter(community_id=community_id, source_fund=fund.value, status='posted')
                .aggregate(t=Sum('amount'))['t'] or Decimal('0')
            )

        data = []
        for e in expenditures:
            data.append({
                'id': str(e.id),
                'reference_number': e.reference_number,
                'source_fund': e.source_fund,
                'source_fund_display': e.get_source_fund_display(),
                'amount': float(e.amount),
                'expenditure_date': e.expenditure_date.isoformat(),
                'description': e.description,
                'signature': e.signature,
                'status': e.status,
                'created_by': e.created_by.fullname or e.created_by.email if e.created_by else '—',
                'season': e.season.title if e.season else None,
            })

        return JsonResponse({
            'success': True,
            'expenditures': data,
            'stats': stats,
        })

    def post(self, request, community_id):
        try:
            body = json.loads(request.body)
            community = get_object_or_404(Community, id=community_id)

            source_fund = body.get('source_fund', '').strip()
            amount_raw = body.get('amount')
            description = body.get('description', '').strip()
            expenditure_date = body.get('expenditure_date')
            signature = body.get('signature', '')
            season_id = body.get('season_id')

            # — Validation —
            if not source_fund:
                return JsonResponse({'success': False, 'message': 'Source fund is required.'}, status=400)

            if source_fund not in [f.value for f in SPENDABLE_FUNDS]:
                return JsonResponse({'success': False, 'message': f'"{source_fund}" is not a valid spendable fund.'}, status=400)

            if not amount_raw:
                return JsonResponse({'success': False, 'message': 'Amount is required.'}, status=400)

            try:
                amount = Decimal(str(amount_raw))
            except Exception:
                return JsonResponse({'success': False, 'message': 'Invalid amount.'}, status=400)

            if amount <= 0:
                return JsonResponse({'success': False, 'message': 'Amount must be greater than zero.'}, status=400)

            if not description:
                return JsonResponse({'success': False, 'message': 'Description is required.'}, status=400)

            if not expenditure_date:
                return JsonResponse({'success': False, 'message': 'Expenditure date is required.'}, status=400)

            # — Balance check —
            available = _get_community_fund_balance(community_id, source_fund)
            if amount > available:
                return JsonResponse({
                    'success': False,
                    'message': f'Insufficient balance in {source_fund.replace("_", " ").title()} fund. Available: XAF {available:,.0f}.'
                }, status=400)

            # — Write —
            with transaction.atomic():
                season = None
                if season_id:
                    season = FinancialSeason.objects.filter(id=season_id, community=community).first()

                expenditure = Expenditure.objects.create(
                    community=community,
                    season=season,
                    source_fund=source_fund,
                    amount=amount,
                    expenditure_date=expenditure_date,
                    description=description,
                    signature=signature,
                    created_by=request.user,
                    status='posted',
                )

            return JsonResponse({
                'success': True,
                'message': f'Expenditure {expenditure.reference_number} recorded successfully.',
                'reference_number': expenditure.reference_number,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


class ExpenditureDetailAPI(View):
    """Handles operations on a single Expenditure (DELETE)."""

    def delete(self, request, community_id, expenditure_id):
        try:
            expenditure = Expenditure.objects.get(id=expenditure_id, community_id=community_id)
            ref = expenditure.reference_number
            expenditure.delete()
            return JsonResponse({'success': True, 'message': f'Expenditure {ref} deleted successfully.'})
        except Expenditure.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Expenditure not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

