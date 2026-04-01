from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from apps.communities.models import Community, Membership
from apps.finance.models import Loan, LoanProduct, LoanApplication, FinancialSeason, LoanPenalty
from apps.global_data.enum import LoanStatus, LoanApplicationStatus, RepaymentFrequency
from apps.finance.tasks import apply_monthly_loan_penalties

User = get_user_model()

class LoanPenaltyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password123')
        from apps.communities.models import CommunitySpace
        self.space = CommunitySpace.objects.create(name='Test Space')
        self.community = Community.objects.create(
            community_space=self.space,
            name='Test Community',
            slug='test-community',
            code='TC001',
            community_type='savings'
        )
        self.membership = Membership.objects.create(
            user=self.user,
            community=self.community,
            status='active',
            joined_at=timezone.now().date()
        )
        self.season = FinancialSeason.objects.create(community=self.community, season_date=timezone.now().date())
        self.product = LoanProduct.objects.create(
            community=self.community,
            name='Test Product',
            min_amount=Decimal('1000'),
            max_amount=Decimal('100000'),
            interest_rate=Decimal('12'), # 12% total for term
            max_term_months=12
        )
        
    def create_loan(self, amount, term_months, maturity_date, amount_paid=Decimal('0')):
        app = LoanApplication.objects.create(
            membership=self.membership,
            loan_product=self.product,
            season=self.season,
            amount_requested=amount,
            proposed_term_months=term_months,
            repayment_frequency=RepaymentFrequency.MONTHLY,
            status=LoanApplicationStatus.APPROVED
        )
        loan = Loan.objects.create(
            application=app,
            membership=self.membership,
            season=self.season,
            amount_borrowed=amount,
            interest_to_be_paid=(amount * self.product.interest_rate) / 100,
            borrow_date=maturity_date - relativedelta(months=term_months),
            maturity_date=maturity_date,
            status=LoanStatus.ACTIVE,
            amount_paid=amount_paid
        )
        return loan

    def test_overdue_penalty_application(self):
        """Test that a loan past maturity gets a penalty."""
        # Loan matured 1 month and 1 day ago
        today = timezone.now().date()
        maturity_date = today - relativedelta(months=1, days=1)
        loan = self.create_loan(Decimal('10000'), 12, maturity_date)
        
        # Run task
        apply_monthly_loan_penalties()
        
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.OVERDUE)
        
        # Verify penalty
        penalties = loan.penalties.all()
        self.assertEqual(penalties.count(), 1)
        
        penalty = penalties.first()
        # monthly_rate = (12% / 12 months) * 2 = 2%
        # penalty = 10000 + 1200 (interest) = 11200 * 0.02 = 224
        expected_rate = Decimal('2.00')
        expected_amount = (Decimal('11200') * expected_rate) / 100
        self.assertEqual(penalty.amount, expected_amount)
        self.assertEqual(penalty.penalty_rate, expected_rate)

    def test_idempotency(self):
        """Test that running the task multiple times doesn't create duplicate penalties."""
        today = timezone.now().date()
        maturity_date = today - relativedelta(months=1, days=5)
        loan = self.create_loan(Decimal('10000'), 12, maturity_date)
        
        # Run task twice
        apply_monthly_loan_penalties()
        apply_monthly_loan_penalties()
        
        self.assertEqual(loan.penalties.count(), 1)

    def test_paid_loan_no_penalty(self):
        """Test that a fully paid loan gets no penalty even if past maturity."""
        today = timezone.now().date()
        maturity_date = today - relativedelta(months=1, days=1)
        # Total to pay is 11200
        loan = self.create_loan(Decimal('10000'), 12, maturity_date, amount_paid=Decimal('11200'))
        loan.status = LoanStatus.PAID
        loan.save()
        
        apply_monthly_loan_penalties()
        
        self.assertEqual(loan.penalties.count(), 0)
        self.assertEqual(loan.status, LoanStatus.PAID)

    def test_sequential_penalties(self):
        """Test catching up on multiple missed penalty months."""
        today = timezone.now().date()
        # Matured 2 months and 5 days ago
        maturity_date = today - relativedelta(months=2, days=5)
        loan = self.create_loan(Decimal('10000'), 12, maturity_date)
        
        apply_monthly_loan_penalties()
        
        self.assertEqual(loan.penalties.count(), 2)
        
        # Verify base amounts increase
        p1 = loan.penalties.get(period_marker=(maturity_date + relativedelta(months=1)).strftime("%Y-%m"))
        p2 = loan.penalties.get(period_marker=(maturity_date + relativedelta(months=2)).strftime("%Y-%m"))
        
        self.assertEqual(p1.base_amount, Decimal('11200')) # Principal + Interest
        self.assertEqual(p2.base_amount, Decimal('11200') + p1.amount) # Principal + Interest + P1

    def test_partial_repayment_affects_penalty(self):
        """Test that partial repayments reduce the base for the next penalty."""
        today = timezone.now().date()
        maturity_date = today - relativedelta(months=2, days=5)
        # Paid 5000 already
        loan = self.create_loan(Decimal('10000'), 12, maturity_date, amount_paid=Decimal('5000'))
        
        apply_monthly_loan_penalties()
        
        p1 = loan.penalties.get(period_marker=(maturity_date + relativedelta(months=1)).strftime("%Y-%m"))
        # Initial Balance = 11200. After 5000 paid = 6200.
        self.assertEqual(p1.base_amount, Decimal('6200'))
