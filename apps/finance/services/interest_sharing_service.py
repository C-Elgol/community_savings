from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from apps.finance.models import (
    Contribution, FinancialSeason, InterestDistribution, InterestPayout,
    Expenditure, Wallet, Transaction
)
from apps.communities.models import Membership
from apps.global_data.enum import CommunityFeatureType, ContributionStatus, ExpenditureStatus

class InterestSharingService:
    """
    Handles time-weighted interest distribution logic and payout recording.
    """
    def __init__(self, community):
        self.community = community

    def calculate_distribution_preview(self, season_id, total_interest_pool):
        """
        Calculates the time-weighted share for each member in a season.
        Formula: weight = amount * (days_until_end_of_season)
        """
        season = FinancialSeason.objects.get(id=season_id)
        # We define "end of season" as the season_date or today if season is open
        end_date = season.season_date
        
        # 1. Get all PAID savings contributions for this season
        contributions = Contribution.objects.filter(
            cycle__season=season,
            feature_type=CommunityFeatureType.SAVINGS,
            status=ContributionStatus.PAID
        ).select_related('membership__user')

        member_data = {} # membership_id -> {total_savings, weighted_savings}
        total_weighted_savings = Decimal("0.00")

        for contrib in contributions:
            mid = str(contrib.membership_id)
            if mid not in member_data:
                member_data[mid] = {
                    'membership_id': mid,
                    'member_name': contrib.membership.user.fullname or contrib.membership.user.email,
                    'total_savings': Decimal("0.00"),
                    'weighted_savings': Decimal("0.00")
                }
            
            # Days held = (end_date - paid_at_date).days
            # If paid_at is after end_date (shouldn't happen), weight is 0
            paid_date = contrib.paid_at.date()
            # We add +1 to ensure that even saving on the last day gives a weight of 1
            days_held = (end_date - paid_date).days + 1
            if days_held < 1: days_held = 1
            
            # Weight = Amount * Days
            weight = contrib.amount_paid * Decimal(str(days_held))
            
            member_data[mid]['total_savings'] += contrib.amount_paid
            member_data[mid]['weighted_savings'] += weight
            total_weighted_savings += weight

        # 2. Calculate Shares
        results = []
        for mid, data in member_data.items():
            share_ratio = Decimal("0.00")
            if total_weighted_savings > 0:
                share_ratio = data['weighted_savings'] / total_weighted_savings
            
            interest_amount = Decimal(str(total_interest_pool)) * share_ratio
            
            results.append({
                'membership_id': mid,
                'member_name': data['member_name'],
                'total_savings': str(data['total_savings']),
                'weighted_savings': str(data['weighted_savings']),
                'share_percentage': round(float(share_ratio * 100), 4),
                'interest_amount': str(round(interest_amount, 2))
            })
        
        return {
            'season_title': season.title or str(season.season_date),
            'total_interest_pool': str(total_interest_pool),
            'total_weighted_savings': str(total_weighted_savings),
            'member_breakdown': results
        }

    @transaction.atomic
    def process_distribution(self, season_id, total_interest_pool, performed_by):
        """
        Initializes the distribution and payout records for a season.
        """
        preview = self.calculate_distribution_preview(season_id, total_interest_pool)
        season = FinancialSeason.objects.get(id=season_id)
        
        # 1. Create the master distribution record
        distribution = InterestDistribution.objects.create(
            community=self.community,
            season=season,
            total_interest_pool=Decimal(str(total_interest_pool)),
            total_weighted_savings=Decimal(preview['total_weighted_savings']),
            distributed_by=performed_by
        )

        # 2. Create the payout records
        payout_data = []
        for item in preview['member_breakdown']:
            membership = Membership.objects.get(id=item['membership_id'])
            payout = InterestPayout.objects.create(
                distribution=distribution,
                membership=membership,
                total_savings=Decimal(item['total_savings']),
                weighted_savings=Decimal(item['weighted_savings']),
                share_percentage=Decimal(str(item['share_percentage'])),
                interest_amount=Decimal(item['interest_amount'])
            )
            payout_data.append({
                'payout_id': str(payout.id),
                'membership_id': item['membership_id'],
                'interest_amount': item['interest_amount']
            })
            
        return distribution, payout_data

    @transaction.atomic
    def record_payout(self, payout_id, performed_by):
        """
        Records the actual payout for a member.
        - Updates Expenditure (Group ledger)
        - Updates Wallet & Transaction (Member ledger)
        """
        payout = InterestPayout.objects.select_for_update().get(id=payout_id)
        if payout.is_paid:
            raise ValueError("This payout has already been recorded.")

        # Total payout = Savings + Interest
        total_payout = payout.total_savings + payout.interest_amount

        # 1. Create Group Expenditure
        expenditure = Expenditure.objects.create(
            community=payout.distribution.community,
            season=payout.distribution.season,
            source_fund=CommunityFeatureType.SAVINGS,
            amount=total_payout,
            expenditure_date=timezone.now().date(),
            description=f"Savings + Interest Payout to {payout.membership.user.fullname} for season {payout.distribution.season.title}",
            status=ExpenditureStatus.POSTED,
            created_by=performed_by
        )

        # 2. Update Member Wallet and Record Transaction
        wallet, _ = Wallet.objects.get_or_create(membership=payout.membership)
        wallet.balance += total_payout
        wallet.save()

        transaction = Transaction.objects.create(
            membership=payout.membership,
            amount=total_payout,
            transaction_type="interest_payout",
            reference=f"INT-PAY-{payout.id.hex[:8].upper()}",
            description=f"Received savings and interest share for {payout.distribution.season.title}"
        )

        # 3. Update Payout record
        payout.is_paid = True
        payout.paid_at = timezone.now()
        payout.recorded_by = performed_by
        payout.expenditure_reference = expenditure.reference_number
        payout.transaction_reference = transaction.reference
        payout.save()

        return payout
