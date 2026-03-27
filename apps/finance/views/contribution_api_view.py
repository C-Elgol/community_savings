from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.finance.models import FinancialSeason, ContributionCycle, Contribution
from apps.communities.models import Community, Membership
from apps.global_data.enum import ContributionStatus
from django.utils import timezone
from django.db import transaction
import json
from apps.finance.tasks.contribution_tasks import send_contribution_recorded_email_task

class SeasonAPI(View):
    def get(self, request, community_id):
        feature_type = request.GET.get('feature_type')
        filters = {'community_id': community_id}
        if feature_type:
            filters['feature_type'] = feature_type
            
        seasons = FinancialSeason.objects.filter(**filters).values('id', 'title', 'season_date', 'is_closed')
        return JsonResponse({'success': True, 'seasons': list(seasons)})

    def post(self, request, community_id):
        try:
            data = json.loads(request.body)
            community = get_object_or_404(Community, id=community_id)
            season = FinancialSeason.objects.create(
                community=community,
                feature_type=data.get('feature_type'),
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
        memberships = Membership.objects.filter(
            community=cycle.community, 
            status='active',
            feature_participations__feature__feature_type='njangi',
            feature_participations__is_active=True
        ).distinct()
        
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
                'payment_reference': c.payment_reference if c else None,
                'comment': c.comment if c else '',
                'signature': c.signature if c else '',
            })
        
        return JsonResponse({'success': True, 'contributions': data})

    def post(self, request, cycle_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amount_paid = float(data.get('amount_paid', 0))
            comment = data.get('comment', '')
            signature = data.get('signature', '')
            
            cycle = get_object_or_404(ContributionCycle, id=cycle_id)
            membership = get_object_or_404(Membership, id=membership_id)
            
            contribution, created = Contribution.objects.get_or_create(
                membership=membership,
                cycle=cycle,
                defaults={'expected_amount': cycle.expected_amount}
            )
            
            contribution.amount_paid = amount_paid
            contribution.comment = comment
            contribution.signature = signature
            
            # Auto-generate payment reference if not already set or if newly paid
            if not contribution.payment_reference and amount_paid > 0:
                from django.db.models import Max
                import re
                
                last_ref = Contribution.objects.filter(
                    cycle__community=cycle.community,
                    payment_reference__startswith='PAY'
                ).aggregate(Max('payment_reference'))['payment_reference__max']
                
                if last_ref:
                    match = re.search(r'PAY(\d+)', last_ref)
                    if match:
                        num = int(match.group(1))
                        contribution.payment_reference = f"PAY{(num + 1):03d}"
                    else:
                        contribution.payment_reference = "PAY001"
                else:
                    contribution.payment_reference = "PAY001"
            
            expected = float(contribution.expected_amount)
            if amount_paid >= expected:
                contribution.status = ContributionStatus.PAID
            elif amount_paid > 0:
                contribution.status = ContributionStatus.PARTIAL
            else:
                contribution.status = ContributionStatus.PENDING
            
            contribution.paid_at = timezone.now() if amount_paid > 0 else None
            contribution.received_by = request.user if amount_paid > 0 else None
            contribution.save()
            
            # Send notification email if amount is paid
            if amount_paid > 0:
                transaction.on_commit(lambda: send_contribution_recorded_email_task.delay(str(contribution.id)))
            
            return JsonResponse({
                'success': True, 
                'message': 'Contribution recorded successfully',
                'payment_reference': contribution.payment_reference
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


VALID_FEATURE_TYPES = {'savings', 'entertainment', 'sinking_fund', 'project', 'events'}


class ContributionCycleAPI(View):
    """Cycles API for non-Njangi feature types (Savings, Entertainment, Sinking Fund, Project)."""

    def get(self, request, season_id):
        feature_type = request.GET.get('feature_type', '')
        if feature_type not in VALID_FEATURE_TYPES:
            return JsonResponse({'success': False, 'message': 'Invalid feature type'}, status=400)

        cycles = ContributionCycle.objects.filter(
            season_id=season_id,
            feature_type=feature_type
        ).values('id', 'title', 'due_date', 'expected_amount', 'is_closed')
        return JsonResponse({'success': True, 'cycles': list(cycles)})

    def post(self, request, season_id):
        try:
            data = json.loads(request.body)
            feature_type = data.get('feature_type', '')
            if feature_type not in VALID_FEATURE_TYPES:
                return JsonResponse({'success': False, 'message': 'Invalid feature type'}, status=400)

            season = get_object_or_404(FinancialSeason, id=season_id)

            # Validate that the feature is enabled in this community
            if not season.community.features.filter(feature_type=feature_type, is_active=True).exists():
                return JsonResponse({'success': False, 'message': f'{feature_type} is not enabled in this community.'}, status=400)

            cycle = ContributionCycle.objects.create(
                community=season.community,
                season=season,
                feature_type=feature_type,
                title=data.get('title'),
                due_date=data.get('due_date'),
                expected_amount=data.get('expected_amount'),
                is_special=data.get('is_special', False)
            )
            return JsonResponse({'success': True, 'message': 'Cycle created successfully', 'cycle_id': str(cycle.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class ContributionRecordAPI(View):
    """Contributions API for non-Njangi feature types."""

    def get(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        feature_type = cycle.feature_type

        if not feature_type or feature_type not in VALID_FEATURE_TYPES:
            return JsonResponse({'success': False, 'message': 'Invalid cycle feature type'}, status=400)

        memberships = Membership.objects.filter(
            community=cycle.community,
            status='active',
            feature_participations__feature__feature_type=feature_type,
            feature_participations__is_active=True
        ).select_related('user').distinct()

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
                'payment_reference': c.payment_reference if c else None,
                'comment': c.comment if c else '',
                'signature': c.signature if c else '',
            })

        return JsonResponse({'success': True, 'contributions': data})

    def post(self, request, cycle_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amount_paid = float(data.get('amount_paid', 0))
            comment = data.get('comment', '')
            signature = data.get('signature', '')

            cycle = get_object_or_404(ContributionCycle, id=cycle_id)
            membership = get_object_or_404(Membership, id=membership_id)

            contribution, created = Contribution.objects.get_or_create(
                membership=membership,
                cycle=cycle,
                defaults={'expected_amount': cycle.expected_amount}
            )

            contribution.amount_paid = amount_paid
            contribution.comment = comment
            contribution.signature = signature

            # Auto-generate payment reference
            if not contribution.payment_reference and amount_paid > 0:
                from django.db.models import Max
                import re

                prefix = cycle.feature_type[:3].upper() if cycle.feature_type else 'PAY'
                last_ref = Contribution.objects.filter(
                    cycle__community=cycle.community,
                    payment_reference__startswith=prefix
                ).aggregate(Max('payment_reference'))['payment_reference__max']

                if last_ref:
                    match = re.search(rf'{prefix}(\d+)', last_ref)
                    if match:
                        num = int(match.group(1))
                        contribution.payment_reference = f"{prefix}{(num + 1):03d}"
                    else:
                        contribution.payment_reference = f"{prefix}001"
                else:
                    contribution.payment_reference = f"{prefix}001"

            expected = float(contribution.expected_amount)
            if amount_paid >= expected:
                contribution.status = ContributionStatus.PAID
            elif amount_paid > 0:
                contribution.status = ContributionStatus.PARTIAL
            else:
                contribution.status = ContributionStatus.PENDING

            contribution.paid_at = timezone.now() if amount_paid > 0 else None
            contribution.received_by = request.user if amount_paid > 0 else None
            contribution.save()

            if amount_paid > 0:
                transaction.on_commit(lambda: send_contribution_recorded_email_task.delay(str(contribution.id)))

            return JsonResponse({
                'success': True,
                'message': 'Contribution recorded successfully',
                'payment_reference': contribution.payment_reference
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
