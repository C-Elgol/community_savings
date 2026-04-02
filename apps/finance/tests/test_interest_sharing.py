from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from apps.users.models import User
from apps.communities.models import Community, CommunitySpace, Membership
from apps.finance.models import (
    FinancialSeason, Contribution, InterestDistribution, InterestPayout, 
    ContributionCycle, Wallet, Expenditure, Transaction
)
from apps.finance.services.interest_sharing_service import InterestSharingService
from apps.global_data.enum import CommunityFeatureType, ContributionStatus

class InterestSharingTest(TestCase):
    def setUp(self):
        self.user_admin = User.objects.create_user(email="admin@test.com", password="password")
        self.space = CommunitySpace.objects.create(name="Test Space", owner=self.user_admin)
        self.community = Community.objects.create(community_space=self.space, name="Test Group", code="TG1")
        
        # Create a season ending in 30 days
        self.end_date = timezone.now().date() + timedelta(days=30)
        self.season = FinancialSeason.objects.create(
            community=self.community, 
            season_date=self.end_date,
            title="2026 Season"
        )
        
        self.member1 = User.objects.create_user(email="m1@test.com", password="password", first_name="Member", last_name="One")
        self.member2 = User.objects.create_user(email="m2@test.com", password="password", first_name="Member", last_name="Two")
        
        self.membership1 = Membership.objects.create(community=self.community, user=self.member1, joined_at=timezone.now().date())
        self.membership2 = Membership.objects.create(community=self.community, user=self.member2, joined_at=timezone.now().date())
        
        self.cycle = ContributionCycle.objects.create(
            community=self.community,
            season=self.season, 
            title="January", 
            due_date=timezone.now().date(),
            expected_amount=Decimal("10000.00")
        )
        
        self.service = InterestSharingService(self.community)

    def test_time_weighted_calculation(self):
        """
        Test that interest is shared based on how long money stayed in.
        M1: 10,000 for 30 days (Weight: 300,000)
        M2: 10,000 for 10 days (Weight: 100,000)
        Total Weight: 400,000
        M1 Share: 75%, M2 Share: 25%
        """
        # M1 pays 30 days before end (Today)
        Contribution.objects.create(
            membership=self.membership1, cycle=self.cycle,
            expected_amount=Decimal("10000.00"),
            amount_paid=Decimal("10000.00"), status=ContributionStatus.PAID,
            paid_at=timezone.now(), feature_type=CommunityFeatureType.SAVINGS
        )
        
        # M2 pays 10 days before end (20 days from today)
        m2_pay_date = timezone.now() + timedelta(days=20)
        Contribution.objects.create(
            membership=self.membership2, cycle=self.cycle,
            expected_amount=Decimal("10000.00"),
            amount_paid=Decimal("10000.00"), status=ContributionStatus.PAID,
            paid_at=m2_pay_date, feature_type=CommunityFeatureType.SAVINGS
        )
        
        preview = self.service.calculate_distribution_preview(self.season.id, 4000)
        
        m1_result = next(m for m in preview['member_breakdown'] if m['membership_id'] == str(self.membership1.id))
        m2_result = next(m for m in preview['member_breakdown'] if m['membership_id'] == str(self.membership2.id))
        
        self.assertEqual(float(m1_result['share_percentage']), 75.0)
        self.assertEqual(float(m2_result['share_percentage']), 25.0)
        self.assertEqual(float(m1_result['interest_amount']), 3000.0)
        self.assertEqual(float(m2_result['interest_amount']), 1000.0)

    def test_payout_recording(self):
        """
        Verify that recording a payout updates all ledgers.
        """
        Contribution.objects.create(
            membership=self.membership1, cycle=self.cycle,
            expected_amount=Decimal("10000.00"),
            amount_paid=Decimal("10000.00"), status=ContributionStatus.PAID,
            paid_at=timezone.now(), feature_type=CommunityFeatureType.SAVINGS
        )
        
        dist, payouts = self.service.process_distribution(self.season.id, 1000, self.user_admin)
        payout_id = payouts[0]['payout_id']
        
        self.service.record_payout(payout_id, self.user_admin)
        
        # Check InterestPayout
        payout = InterestPayout.objects.get(id=payout_id)
        self.assertTrue(payout.is_paid)
        self.assertIsNotNone(payout.paid_at)
        
        # Check Wallet
        wallet = Wallet.objects.get(membership=self.membership1)
        self.assertEqual(wallet.balance, Decimal("1000.00"))
        
        # Check Transaction
        transaction = Transaction.objects.get(membership=self.membership1, transaction_type="interest_payout")
        self.assertEqual(transaction.amount, Decimal("1000.00"))
        
        # Check Expenditure
        expenditure = Expenditure.objects.get(reference_number=payout.expenditure_reference)
        self.assertEqual(expenditure.amount, Decimal("1000.00"))
        self.assertEqual(expenditure.source_fund, CommunityFeatureType.SAVINGS)
