from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from apps.finance.models import Loan, LoanPenalty
from apps.global_data.enum import LoanStatus
import logging

logger = logging.getLogger(__name__)

@shared_task
def apply_monthly_loan_penalties():
    """
    Daily task to detect overdue loans and apply monthly penalties.
    A penalty is applied starting from the first full month after maturity.
    Rate = 2 * (Original Term Interest / Term Months).
    """
    today = timezone.now().date()
    
    # Get all loans that are past maturity and not fully paid
    overdue_loans = Loan.objects.exclude(status=LoanStatus.PAID).filter(maturity_date__lt=today)
    
    for loan in overdue_loans:
        try:
            with transaction.atomic():
                # Re-fetch with lock to avoid race conditions
                loan = Loan.objects.select_for_update().get(id=loan.id)
                
                if loan.status == LoanStatus.PAID:
                    continue
                
                # Update status to OVERDUE if it's not already
                if loan.status != LoanStatus.OVERDUE:
                    loan.status = LoanStatus.OVERDUE
                    loan.save(update_fields=['status'])
                
                # Calculate penalty rate (monthly)
                # Formula: 2 * (initial_interest_rate / term_months)
                term_months = loan.application.proposed_term_months or 1
                original_rate = loan.application.loan_product.interest_rate
                monthly_penalty_rate = (original_rate / term_months) * 2
                
                # Identify penalty periods
                # First penalty is due 1 month after maturity
                start_date = loan.maturity_date + relativedelta(months=1)
                
                current_period_date = start_date
                while current_period_date <= today:
                    period_marker = current_period_date.strftime("%Y-%m")
                    
                    # Check if penalty already exists for this month
                    if not LoanPenalty.objects.filter(loan=loan, period_marker=period_marker).exists():
                        # Calculate current outstanding balance
                        # This property takes into account amount_borrowed + interest + existing_penalties - amount_paid
                        base_amount = loan.outstanding_balance
                        
                        if base_amount > 0:
                            penalty_amount = (base_amount * monthly_penalty_rate) / 100
                            
                            LoanPenalty.objects.create(
                                loan=loan,
                                amount=penalty_amount,
                                penalty_rate=monthly_penalty_rate,
                                base_amount=base_amount,
                                period_marker=period_marker
                            )
                            logger.info(f"Applied penalty of {penalty_amount} to loan {loan.id} for period {period_marker}")
                        else:
                            # Loan is fully paid (outstanding is 0 or less)
                            # We can mark it as paid here if it wasn't already
                            loan.status = LoanStatus.PAID
                            loan.save(update_fields=['status'])
                            break
                    
                    # Move to next month
                    current_period_date += relativedelta(months=1)
                    
        except Exception as e:
            logger.error(f"Error applying penalty to loan {loan.id}: {str(e)}")
