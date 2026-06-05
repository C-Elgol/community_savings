import os
import django
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Avg

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.communities.models import Membership
from apps.analytics.models import MemberBehaviorSnapshot, CreditProfile
from apps.analytics.services.scoring_service import CreditScoringService
from apps.finance.models import Loan, LoanRepaymentSchedule, Contribution 
from apps.global_data.enum import ContributionStatus, LoanStatus

User = get_user_model()
try:
    user = User.objects.get(email='creatorelgol@gmail.com')
    membership = Membership.objects.filter(user=user, status='active').first()
    if not membership:
        membership = Membership.objects.filter(user=user).first()
    
    print(f"Targeting User: {user.email}")
    print(f"Membership ID: {membership.id}")
    
    service = CreditScoringService()
    
    # 1. contribution_consistency
    consist = service._calculate_savings_consistency(membership)
    
    # 2. repayment_punctuality
    repay = service._calculate_repayment_reliability(membership)
    
    # 4. attendance_score
    attend = service._calculate_engagement(membership)
    
    # 5. savings_stability (This is a derived score, but let's use the method)
    stability = service._calculate_financial_stability(membership)
    
    # 6. loan_to_savings_ratio
    total_savings = Contribution.objects.filter(
        membership=membership,
        status=ContributionStatus.PAID
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    
    active_loans_balance = Loan.objects.filter(
        membership=membership,
        status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.DEFAULTED]
    ).aggregate(total=Sum('amount_borrowed'))['total'] or Decimal('0')
    
    ratio = active_loans_balance / total_savings if total_savings > 0 else Decimal('0')
    
    # 3. default_history (Probability of default)
    profile = CreditProfile.objects.filter(membership=membership).first()
    default_hist = profile.probability_of_default if profile else (Decimal('1.0') - stability) # Fallback

    # 7. average_overdue_days
    overdue_schedules = LoanRepaymentSchedule.objects.filter(
        loan__membership=membership,
        is_paid=False,
        due_date__lt=timezone.now().date()
    )
    if overdue_schedules.exists():
        total_days = 0
        today = timezone.now().date()
        for s in overdue_schedules:
            total_days += (today - s.due_date).days
        avg_overdue = total_days / overdue_schedules.count()
    else:
        avg_overdue = 0

    # 8. current_unpaid_loans
    unpaid_count = Loan.objects.filter(
        membership=membership,
        status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.DEFAULTED, LoanStatus.UNPAID]
    ).count()

    result = {
        "contribution_consistency": float(consist),
        "repayment_punctuality": float(repay),
        "default_history": float(default_hist),
        "attendance_score": float(attend),
        "savings_stability": float(stability),
        "loan_to_savings_ratio": float(ratio),
        "average_overdue_days": float(avg_overdue),
        "current_unpaid_loans": int(unpaid_count),
    }
    
    # Format according to user request
    for key, value in result.items():
        print(f"{key}: {value}")
        
except Exception as e:
    import traceback
    print('Error:', e)
    traceback.print_exc()
