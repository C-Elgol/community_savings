from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.finance.models import (
    Contribution, Loan, LoanPayment, LoanPenalty,
    Fine, FinePayment, Expenditure, RegistrationPayment,
)
from apps.communities.models import Membership
from apps.global_data.enum import CommunityFeatureType, LoanStatus, ContributionStatus


SPENDABLE_FUNDS = [
    CommunityFeatureType.ENTERTAINMENT,
    CommunityFeatureType.PROJECT,
    CommunityFeatureType.SINKING_FUND,
    CommunityFeatureType.EVENTS,
    CommunityFeatureType.SAVINGS,
]

ZERO = Decimal("0.00")


class DashboardService:
    """Centralized, reusable financial summary engine for a single community."""

    def __init__(self, community_id):
        self.cid = community_id

    # ── helpers ──────────────────────────────────────────────
    def _sum(self, qs, field='amount'):
        return qs.aggregate(t=Sum(field))['t'] or ZERO

    # ── INFLOWS ──────────────────────────────────────────────
    def total_contributions(self):
        return self._sum(
            Contribution.objects.filter(
                cycle__community_id=self.cid,
                status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL],
            ),
            'amount_paid',
        )

    def total_contributions_by_fund(self, fund):
        """Contributions for a specific feature_type."""
        return self._sum(
            Contribution.objects.filter(
                cycle__community_id=self.cid,
                feature_type=fund,
                status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL],
            ),
            'amount_paid',
        )

    def total_loan_repayments(self):
        return self._sum(
            LoanPayment.objects.filter(loan__membership__community_id=self.cid)
        )

    def total_fine_payments(self):
        return self._sum(
            FinePayment.objects.filter(fine__membership__community_id=self.cid)
        )

    def total_registration_fees(self):
        return self._sum(
            RegistrationPayment.objects.filter(
                application__community_id=self.cid,
                is_confirmed=True,
            )
        )

    def total_inflows(self):
        return (
            self.total_contributions()
            + self.total_loan_repayments()
            + self.total_fine_payments()
            + self.total_registration_fees()
        )

    # ── OUTFLOWS ─────────────────────────────────────────────
    def total_loans_disbursed(self):
        return self._sum(
            Loan.objects.filter(
                membership__community_id=self.cid,
            ).exclude(status=LoanStatus.CANCELLED),
            'amount_borrowed',
        )

    def total_expenditures(self):
        return self._sum(
            Expenditure.objects.filter(
                community_id=self.cid,
                status='posted',
            )
        )

    def total_outflows(self):
        return self.total_loans_disbursed() + self.total_expenditures()

    # ── NET BALANCE ──────────────────────────────────────────
    def net_balance(self):
        return self.total_inflows() - self.total_outflows()

    # ── LOAN STATS ───────────────────────────────────────────
    def loan_stats(self):
        active_loans = Loan.objects.filter(
            membership__community_id=self.cid,
        ).exclude(status__in=[LoanStatus.CANCELLED, LoanStatus.PAID])

        interest_earned = self._sum(
            Loan.objects.filter(membership__community_id=self.cid)
                .exclude(status=LoanStatus.CANCELLED),
            'interest_to_be_paid',
        )

        penalties_earned = self._sum(
            LoanPenalty.objects.filter(loan__membership__community_id=self.cid)
        )

        outstanding = active_loans.aggregate(
            total=Sum('amount_borrowed')
        )['total'] or ZERO

        return {
            'total_disbursed': str(self.total_loans_disbursed()),
            'outstanding': str(outstanding),
            'total_repaid': str(self.total_loan_repayments()),
            'interest_earned': str(interest_earned),
            'penalties_earned': str(penalties_earned),
            'active_count': active_loans.count(),
        }

    # ── FUND BALANCES ────────────────────────────────────────
    def fund_balances(self):
        balances = {}
        for fund in SPENDABLE_FUNDS:
            inflow = self.total_contributions_by_fund(fund.value)
            outflow = self._sum(
                Expenditure.objects.filter(
                    community_id=self.cid,
                    source_fund=fund.value,
                    status='posted',
                )
            )
            balances[fund.value] = str(inflow - outflow)
        return balances

    # ── MEMBER COUNT ─────────────────────────────────────────
    def total_members(self):
        return Membership.objects.filter(
            community_id=self.cid,
            status='active',
        ).count()

    # ── RECENT ACTIVITY ──────────────────────────────────────
    def recent_contributions(self, limit=5):
        qs = Contribution.objects.filter(
            cycle__community_id=self.cid,
            status__in=[ContributionStatus.PAID, ContributionStatus.PARTIAL],
        ).select_related('membership__user', 'cycle').order_by('-paid_at')[:limit]

        return [{
            'member': c.membership.user.fullname or c.membership.user.email,
            'amount': float(c.amount_paid),
            'feature': c.get_feature_type_display() if c.feature_type else 'Njangi',
            'date': c.paid_at.isoformat() if c.paid_at else None,
        } for c in qs]

    def recent_repayments(self, limit=5):
        qs = LoanPayment.objects.filter(
            loan__membership__community_id=self.cid,
        ).select_related('loan__membership__user').order_by('-payment_date')[:limit]

        return [{
            'member': p.loan.membership.user.fullname or p.loan.membership.user.email,
            'amount': float(p.amount),
            'date': p.payment_date.isoformat(),
        } for p in qs]

    def recent_expenditures(self, limit=5):
        qs = Expenditure.objects.filter(
            community_id=self.cid,
            status='posted',
        ).order_by('-expenditure_date')[:limit]

        return [{
            'reference': e.reference_number,
            'source_fund': e.get_source_fund_display(),
            'amount': float(e.amount),
            'description': e.description[:80],
            'date': e.expenditure_date.isoformat(),
        } for e in qs]

    # ── FULL PAYLOAD ─────────────────────────────────────────
    def full_summary(self):
        """Build the complete dashboard JSON payload in a single call."""
        total_in = self.total_inflows()
        total_out = self.total_outflows()

        return {
            'summary': {
                'total_inflows': str(total_in),
                'total_outflows': str(total_out),
                'net_balance': str(total_in - total_out),
                'total_members': self.total_members(),
                'total_contributions': str(self.total_contributions()),
                'total_expenditures': str(self.total_expenditures()),
                'total_fines_collected': str(self.total_fine_payments()),
            },
            'fund_balances': self.fund_balances(),
            'loan_stats': self.loan_stats(),
            'recent': {
                'contributions': self.recent_contributions(),
                'repayments': self.recent_repayments(),
                'expenditures': self.recent_expenditures(),
            },
        }
