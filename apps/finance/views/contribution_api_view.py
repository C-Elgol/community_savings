from django.http import JsonResponse
from django.views import View
from django.shortcuts import get_object_or_404
from apps.finance.models import FinancialSeason, ContributionCycle, Contribution
from apps.communities.models import Community, Membership
from apps.global_data.enum import ContributionStatus, CommunityFeatureType
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
import json
from apps.finance.tasks.contribution_tasks import send_contribution_recorded_email_task

class SeasonAPI(View):
    def get(self, request, community_id):
        filters = {'community_id': community_id}
        seasons = FinancialSeason.objects.filter(**filters).values('id', 'title', 'season_date', 'is_closed')
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
                expected_amount=data.get('expected_amount') or 0,
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
        
        contributions = Contribution.objects.filter(cycle=cycle, feature_type="njangi")
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
                feature_type='njangi',
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
                    payment_reference__startswith='PAY',
                    feature_type='njangi'
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
            
            if amount_paid > 0:
                contribution.status = ContributionStatus.PAID
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
        # feature_type is now optional for stats calculation.

        # Existence check
        from django.http import Http404
        try:
            season = get_object_or_404(FinancialSeason, id=season_id)
        except Http404:
            return JsonResponse({'success': False, 'message': f'Financial Season with ID {season_id} not found'}, status=404)

        cycles_qs = ContributionCycle.objects.filter(
            season_id=season_id
        ).order_by('due_date')
        
        # Get members count for this feature to calculate total expected
        from apps.communities.models import Membership
        memberships_count = Membership.objects.filter(
            community=season.community,
            status='active',
            feature_participations__feature__feature_type=feature_type,
            feature_participations__is_active=True
        ).distinct().count()
        
        cycles_data = []
        grand_total = 0
        for cycle in cycles_qs:
            total_collected = Contribution.objects.filter(
                cycle=cycle,
                status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
            
            total_collected = float(total_collected)
            grand_total += total_collected
            
            total_expected = float(cycle.expected_amount) * memberships_count
            
            cycles_data.append({
                'id': str(cycle.id),
                'title': cycle.title,
                'due_date': cycle.due_date.isoformat(),
                'expected_amount': str(cycle.expected_amount),
                'total_expected': str(total_expected),
                'is_closed': cycle.is_closed,
                'total_collected': str(total_collected)
            })

        return JsonResponse({
            'success': True, 
            'cycles': cycles_data,
            'net_income': str(grand_total) if feature_type else "0.00"
        })

    def post(self, request, season_id):
        try:
            data = json.loads(request.body)
            feature_type = data.get('feature_type')

            from django.http import Http404
            try:
                season = get_object_or_404(FinancialSeason, id=season_id)
            except Http404:
                return JsonResponse({'success': False, 'message': f'Financial Season with ID {season_id} not found'}, status=404)

            # Validate that the season exists (already done by get_object_or_404)
            
            cycle = ContributionCycle.objects.create(
                community=season.community,
                season=season,
                title=data.get('title'),
                due_date=data.get('due_date'),
                expected_amount=data.get('expected_amount') or 0,
                is_special=data.get('is_special', False)
            )
            return JsonResponse({'success': True, 'message': 'Cycle created successfully', 'cycle_id': str(cycle.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class ContributionRecordAPI(View):
    """Contributions API for non-Njangi feature types."""

    def get(self, request, cycle_id):
        cycle = get_object_or_404(ContributionCycle, id=cycle_id)
        feature_type = request.GET.get('feature_type')

        if not feature_type or feature_type not in VALID_FEATURE_TYPES:
            return JsonResponse({'success': False, 'message': 'Invalid cycle feature type'}, status=400)

        memberships = Membership.objects.filter(
            community=cycle.community,
            status='active',
            feature_participations__feature__feature_type=feature_type,
            feature_participations__is_active=True
        ).select_related('user').distinct()

        contributions = Contribution.objects.filter(cycle=cycle, feature_type=feature_type)
        contrib_map = {str(c.membership_id): c for c in contributions}

        # Fetch season totals for all members in this season/feature
        season_totals = Contribution.objects.filter(
            cycle__season=cycle.season,
            feature_type=feature_type,
            status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL]
        ).values('membership_id').annotate(total=Sum('amount_paid'))
        
        totals_map = {str(item['membership_id']): item['total'] for item in season_totals}

        data = []
        for m in memberships:
            c = contrib_map.get(str(m.id))
            data.append({
                'membership_id': str(m.id),
                'member_name': m.user.get_full_name,
                'amount_paid': str(c.amount_paid) if c else '0.00',
                'total_season_amount': str(totals_map.get(str(m.id), '0.00')),
                'status': c.status if c else ContributionStatus.PENDING,
                'paid_at': c.paid_at.isoformat() if c and c.paid_at else None,
                'payment_reference': c.payment_reference if c else None,
                'comment': c.comment if c else '',
                'features': list(m.feature_participations.filter(is_active=True).values_list('feature__feature_type', flat=True)),
                'signature': c.signature if c else '',
            })

        return JsonResponse({'success': True, 'contributions': data})

    def post(self, request, cycle_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            feature_type = data.get('feature_type')
            amount_paid = float(data.get('amount_paid', 0))
            comment = data.get('comment', '')
            signature = data.get('signature', '')

            cycle = get_object_or_404(ContributionCycle, id=cycle_id)
            membership = get_object_or_404(Membership, id=membership_id)

            contribution, created = Contribution.objects.get_or_create(
                membership=membership,
                cycle=cycle,
                feature_type=feature_type,
                defaults={'expected_amount': cycle.expected_amount}
            )

            contribution.amount_paid = amount_paid
            contribution.comment = comment
            contribution.signature = signature

            # Auto-generate payment reference
            if not contribution.payment_reference and amount_paid > 0:
                from django.db.models import Max
                import re

                prefix = feature_type[:3].upper() if feature_type else 'PAY'
                last_ref = Contribution.objects.filter(
                    cycle__community=cycle.community,
                    payment_reference__startswith=prefix,
                    feature_type=feature_type
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

            if amount_paid > 0:
                contribution.status = ContributionStatus.PAID
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


class BulkContributionRecordAPI(View):
    def post(self, request, cycle_id):
        try:
            data = json.loads(request.body)
            membership_id = data.get('membership_id')
            amounts = data.get('amounts', {})  # {feature_type: amount, ...}
            comment = data.get('comment', '')
            signature = data.get('signature', '')

            cycle = get_object_or_404(ContributionCycle, id=cycle_id)
            membership = get_object_or_404(Membership, id=membership_id)

            results = []

            with transaction.atomic():
                for feature_type, amount_paid in amounts.items():
                    if amount_paid is None or amount_paid == "":
                        continue

                    try:
                        amount_paid = float(amount_paid)
                    except (ValueError, TypeError):
                        continue

                    if amount_paid < 0:
                        continue
                    
                    # If amount is 0 and no contribution exists, skip it
                    if amount_paid == 0 and not Contribution.objects.filter(membership=membership, cycle=cycle, feature_type=feature_type).exists():
                        continue

                    contribution, created = Contribution.objects.get_or_create(
                        membership=membership,
                        cycle=cycle,
                        feature_type=feature_type,
                        defaults={'expected_amount': cycle.expected_amount}
                    )

                    contribution.amount_paid = amount_paid
                    contribution.comment = comment
                    contribution.signature = signature

                    # Auto-generate payment reference
                    if not contribution.payment_reference and amount_paid > 0:
                        from django.db.models import Max
                        import re

                        prefix = feature_type[:3].upper() if feature_type else 'PAY'
                        last_ref = Contribution.objects.filter(
                            cycle__community=cycle.community,
                            payment_reference__startswith=prefix,
                            feature_type=feature_type
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

                    if amount_paid > 0:
                        contribution.status = ContributionStatus.PAID
                    else:
                        contribution.status = ContributionStatus.PENDING

                    contribution.paid_at = timezone.now() if amount_paid > 0 else None
                    contribution.received_by = request.user if amount_paid > 0 else None
                    contribution.save()

                    if amount_paid > 0:
                        transaction.on_commit(
                            lambda c_id=contribution.id: send_contribution_recorded_email_task.delay(str(c_id))
                        )

                    results.append({
                        'feature_type': feature_type,
                        'payment_reference': contribution.payment_reference,
                        'status': contribution.status,
                        'amount_paid': str(contribution.amount_paid)
                    })

            return JsonResponse({
                'success': True,
                'message': 'Contributions recorded successfully',
                'results': results
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


class MemberSeasonContributionsAPI(View):
    """API to fetch all contributions for a specific member in a season for a feature type."""

    def get(self, request, season_id, membership_id):
        season = get_object_or_404(FinancialSeason, id=season_id)
        membership = get_object_or_404(Membership, id=membership_id)
        feature_type = request.GET.get('feature_type')

        contributions = Contribution.objects.filter(
            membership=membership,
            cycle__season=season,
            feature_type=feature_type
        ).select_related('cycle').order_by('cycle__due_date')

        history = []
        grand_total = 0
        for c in contributions:
            amount = float(c.amount_paid)
            grand_total += amount
            history.append({
                'cycle_title': c.cycle.title,
                'due_date': c.cycle.due_date.isoformat(),
                'amount_paid': str(c.amount_paid),
                'status': c.status,
                'payment_reference': c.payment_reference,
                'paid_at': c.paid_at.isoformat() if c.paid_at else None,
            })

        return JsonResponse({
            'success': True,
            'member_name': membership.user.get_full_name,
            'feature_label': (feature_type or 'contribution').replace('_', ' ').title(),
            'history': history,
            'grand_total': str(grand_total)
        })


class MembershipCycleContributionsAPI(View):
    def get(self, request, cycle_id, membership_id):
        try:
            membership = get_object_or_404(Membership, id=membership_id)
            contributions = Contribution.objects.filter(
                cycle_id=cycle_id,
                membership_id=membership_id
            )
            data = {c.feature_type: str(c.amount_paid) for c in contributions}
            
            # Get features the member is actually enrolled in
            enrolled_features = []
            for ft, label in CommunityFeatureType.choices:
                if membership.has_feature(ft):
                    enrolled_features.append(ft)
                    
            # Get comment and signature from any existing contribution for this cycle
            first_contrib = contributions.first()
            comment = first_contrib.comment if first_contrib else ""
            signature = first_contrib.signature if first_contrib else ""

            return JsonResponse({
                'success': True, 
                'contributions': data,
                'enrolled_features': enrolled_features,
                'comment': comment,
                'signature': signature,
                'is_edit': contributions.exists()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
