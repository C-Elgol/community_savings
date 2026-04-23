from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
import logging

from apps.communities.models import Membership
from apps.finance.models import Contribution, Loan, LoanPayment, Fine, FinancialSeason, ContributionCycle
from apps.meetings.models import Meeting
from apps.analytics.models import CreditProfile

logger = logging.getLogger(__name__)

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'publics/home/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 1. Get Primary Membership (first active one)
        membership = Membership.objects.filter(user=user, status='active').select_related('community').first()
        if not membership:
            context['no_membership'] = True
            return context

        community = membership.community
        today = timezone.now().date()
        
        # Try to get active season for this community
        active_season = FinancialSeason.objects.filter(community=community, is_closed=False).order_by('-season_date').first()

        # 2. Total Contributions (all time)
        total_contributions = Contribution.objects.filter(
            membership=membership, 
            status='paid'
        ).aggregate(total=Sum('amount_paid'))['total'] or 0
        context['total_contributions'] = total_contributions

        # 3. Current Savings (current season)
        current_savings = 0
        if active_season:
            current_savings = Contribution.objects.filter(
                membership=membership,
                cycle__season=active_season,
                status='paid'
            ).aggregate(total=Sum('amount_paid'))['total'] or 0
        context['current_savings'] = current_savings
        
        # 4. Active Loan
        active_loan = Loan.objects.filter(
            membership=membership, 
            status='active'
        ).select_related('application__loan_product').first()
        context['active_loan'] = active_loan
        
        if active_loan:
            # Calculate repayment percentage
            total_to_pay = active_loan.total_repayable_amount
            paid = active_loan.amount_paid
            progress = (paid / total_to_pay * 100) if total_to_pay > 0 else 0
            context['loan_progress'] = round(progress, 1)
            
            # Next loan repayment due
            next_repayment = active_loan.repayment_schedule.filter(is_paid=False, due_date__gte=today).order_by('due_date').first()
            context['next_repayment'] = next_repayment

        # 5. Credit Profile
        credit_profile = CreditProfile.objects.filter(membership=membership).first()
        context['credit_profile'] = credit_profile

        # 6. Next Due (Contribution or Repayment)
        next_cycle = ContributionCycle.objects.filter(
            community=community, 
            due_date__gte=today,
            is_closed=False
        ).order_by('due_date').first()
        
        next_due_amount = 0
        next_due_date = None
        
        if next_cycle:
            # Check if user has already paid for this cycle
            contribution = Contribution.objects.filter(membership=membership, cycle=next_cycle).first()
            if not contribution or contribution.status != 'paid':
                next_due_amount = next_cycle.expected_amount
                next_due_date = next_cycle.due_date
        
        # If loan repayment is sooner, show that
        if active_loan and context.get('next_repayment'):
            repayment = context['next_repayment']
            if not next_due_date or repayment.due_date < next_due_date:
                next_due_amount = repayment.amount_due - repayment.amount_paid
                next_due_date = repayment.due_date
        
        context['next_due_amount'] = next_due_amount
        context['next_due_date'] = next_due_date
        if next_due_date:
            context['days_until_due'] = (next_due_date - today).days

        # 7. Contribution History
        contribution_history = Contribution.objects.filter(
            membership=membership
        ).select_related('cycle').order_by('-cycle__due_date')[:5]
        context['contribution_history'] = contribution_history

        # 8. Upcoming Meetings
        upcoming_meetings = Meeting.objects.filter(
            community=community,
            scheduled_date__gte=today
        ).order_by('scheduled_date')[:3]
        context['upcoming_meetings'] = upcoming_meetings

        # 9. Recent Activity Feed
        # Mix contributions, loan payments, and fines
        activities = []
        
        # Recent paid contributions
        recent_contribs = Contribution.objects.filter(
            membership=membership, 
            status='paid',
            paid_at__isnull=False
        ).order_by('-paid_at')[:5]
        for c in recent_contribs:
            activities.append({
                'type': 'contribution',
                'amount': c.amount_paid,
                'date': c.paid_at,
                'title': f"Contribution {c.cycle.title} recorded",
                'icon': 'fas fa-check',
                'color': 'emerald'
            })
            
        # Recent loan payments
        recent_loan_pays = LoanPayment.objects.filter(
            loan__membership=membership
        ).order_by('-payment_date')[:5]
        for lp in recent_loan_pays:
            activities.append({
                'type': 'loan_payment',
                'amount': lp.amount,
                'date': lp.payment_date,
                'title': f"Loan payment received",
                'icon': 'fas fa-file-signature',
                'color': 'indigo'
            })
            
        # Recent fines
        recent_fines = Fine.objects.filter(
            membership=membership
        ).order_by('-issued_date')[:5]
        for f in recent_fines:
            activities.append({
                'type': 'fine',
                'amount': f.amount,
                'date': f.issued_date,
                'title': f"Fine issued: {f.get_fine_type_display()}",
                'icon': 'fas fa-exclamation',
                'color': 'amber'
            })
            
        # Sort and take top 5
        activities.sort(key=lambda x: x['date'].date() if hasattr(x['date'], 'date') else x['date'], reverse=True)
        context['recent_activities'] = activities[:6]

        return context
