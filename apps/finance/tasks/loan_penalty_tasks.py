from celery import shared_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from apps.finance.models import Loan, LoanPenalty
from apps.global_data.enum import LoanStatus
from apps.global_data.email import EmailUtil
import logging

logger = logging.getLogger(__name__)


@shared_task(name='apps.finance.tasks.send_penalty_notification_task')
def send_penalty_notification_task(loan_id, penalty_id):
    """
    Sends an email to the borrower informing them a penalty has been applied.
    """
    try:
        loan = Loan.objects.select_related(
            'membership__user',
            'application__loan_product',
            'membership__community'
        ).get(id=loan_id)
        penalty = LoanPenalty.objects.get(id=penalty_id)

        user = loan.membership.user
        community = loan.membership.community
        email = user.email
        if not email:
            return

        context = {
            'site_name': community.name,
            'year': timezone.now().year,
            'member_name': user.fullname or user.email,
            'community_name': community.name,
            'penalty_period': penalty.period_marker,
            'penalty_rate': float(penalty.penalty_rate),
            'base_amount': float(penalty.base_amount),
            'penalty_amount': float(penalty.amount),
            'amount_borrowed': float(loan.amount_borrowed),
            'interest': float(loan.interest_to_be_paid),
            'total_penalties': float(loan.total_penalty_charges),
            'amount_paid': float(loan.amount_paid),
            'outstanding_balance': float(loan.outstanding_balance),
        }

        EmailUtil().send_email_with_template(
            template='publics/emails/loan_penalty_applied.html',
            context=context,
            receivers=[email],
            subject=f"[{community.name}] Overdue Loan Penalty Applied — {penalty.period_marker}",
        )
        logger.info(f"Penalty notification sent to {email} for loan {loan_id}")
    except Exception as e:
        logger.error(f"Error sending penalty notification for loan {loan_id}: {e}")


@shared_task(name='apps.finance.tasks.send_loan_maturity_reminders')
def send_loan_maturity_reminders():
    """
    Daily task to send reminder emails to borrowers whose loans mature in exactly 3 days.
    """
    today = timezone.now().date()
    target_date = today + timedelta(days=3)

    loans = Loan.objects.exclude(status=LoanStatus.PAID).filter(
        maturity_date=target_date
    ).select_related(
        'membership__user',
        'application__loan_product',
        'membership__community'
    )

    for loan in loans:
        try:
            user = loan.membership.user
            community = loan.membership.community
            email = user.email
            if not email:
                continue

            # Calculate the expected monthly penalty rate
            term_months = loan.application.proposed_term_months or 1
            original_rate = loan.application.loan_product.interest_rate
            monthly_penalty_rate = (original_rate / term_months) * 2

            context = {
                'site_name': community.name,
                'year': timezone.now().year,
                'member_name': user.fullname or user.email,
                'community_name': community.name,
                'product_name': loan.application.loan_product.name,
                'amount_borrowed': float(loan.amount_borrowed),
                'interest': float(loan.interest_to_be_paid),
                'outstanding_balance': float(loan.outstanding_balance),
                'maturity_date': loan.maturity_date.strftime('%d %B %Y'),
                'days_remaining': 3,
                'penalty_rate': float(monthly_penalty_rate),
            }

            EmailUtil().send_email_with_template(
                template='publics/emails/loan_maturity_reminder.html',
                context=context,
                receivers=[email],
                subject=f"[{community.name}] ⚠️ Your loan matures in 3 days",
            )
            logger.info(f"Maturity reminder sent to {email} for loan {loan.id}")
        except Exception as e:
            logger.error(f"Error sending maturity reminder for loan {loan.id}: {e}")


@shared_task(name='apps.finance.tasks.apply_monthly_loan_penalties')
def apply_monthly_loan_penalties():
    """
    Daily task to detect overdue loans and apply monthly penalties.
    A penalty is applied starting from the first full month after maturity.
    Rate = 2 * (Original Term Interest / Term Months).
    """
    today = timezone.now().date()

    # Get all loans that are past maturity and not fully paid
    overdue_loans = Loan.objects.exclude(status=LoanStatus.PAID).filter(
        maturity_date__lt=today
    ).select_related(
        'membership__user',
        'application__loan_product',
        'membership__community'
    )

    for loan in overdue_loans:
        try:
            with transaction.atomic():
                # Re-fetch with lock to avoid race conditions
                loan = Loan.objects.select_for_update().select_related(
                    'membership__user',
                    'application__loan_product',
                    'membership__community'
                ).get(id=loan.id)

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

                # First penalty is due 1 month after maturity
                start_date = loan.maturity_date + relativedelta(months=1)

                current_period_date = start_date
                while current_period_date <= today:
                    period_marker = current_period_date.strftime("%Y-%m")

                    # Check if penalty already exists for this month (idempotency)
                    if not LoanPenalty.objects.filter(loan=loan, period_marker=period_marker).exists():
                        base_amount = loan.outstanding_balance

                        if base_amount > 0:
                            penalty_amount = (base_amount * monthly_penalty_rate) / 100

                            penalty = LoanPenalty.objects.create(
                                loan=loan,
                                amount=penalty_amount,
                                penalty_rate=monthly_penalty_rate,
                                base_amount=base_amount,
                                period_marker=period_marker
                            )
                            logger.info(f"Applied penalty of {penalty_amount} to loan {loan.id} for period {period_marker}")

                            # Send notification asynchronously
                            send_penalty_notification_task.delay(str(loan.id), str(penalty.id))
                        else:
                            # Loan is fully cleared — mark as paid
                            loan.status = LoanStatus.PAID
                            loan.save(update_fields=['status'])
                            break

                    # Move to next month
                    current_period_date += relativedelta(months=1)

        except Exception as e:
            logger.error(f"Error applying penalty to loan {loan.id}: {str(e)}")
