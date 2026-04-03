from celery import shared_task
import logging
from django.conf import settings
from apps.global_data.email import EmailUtil
from apps.finance.models import Contribution
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

@shared_task(name='apps.finance.tasks.send_contribution_recorded_email_task', bind=True, max_retries=3, default_retry_delay=60)
def send_contribution_recorded_email_task(self, contribution_id):
    """
    Send email to member when their contribution is recorded.
    """
    logger.info(f"Starting send_contribution_recorded_email_task for contribution ID {contribution_id}")
    try:
        contribution = Contribution.objects.select_related('membership', 'membership__user', 'membership__community', 'cycle').get(id=contribution_id)
    except Contribution.DoesNotExist:
        logger.error(f"Contribution {contribution_id} not found.")
        return False

    if not contribution.membership.user.email:
        logger.warning(f"User {contribution.membership.user.id} has no email, skipping notification.")
        return False

    email_util = EmailUtil()
    site_name = getattr(settings, 'SITE_NAME', 'Community Savings')

    context = {
        'first_name': contribution.membership.user.first_name or contribution.membership.user.email.split('@')[0],
        'community_name': contribution.membership.community.name,
        'cycle_title': contribution.cycle.title,
        'amount_paid': contribution.amount_paid,
        'status_display': contribution.get_status_display(),
        'paid_at': contribution.paid_at.strftime('%Y-%m-%d %H:%M') if contribution.paid_at else '',
        'payment_reference': contribution.payment_reference,
        'site_name': site_name,
    }

    success = email_util.send_email_with_template(
        template='publics/emails/contribution_recorded.html',
        context=context,
        receivers=[contribution.membership.user.email],
        subject=_("Contribution Recorded - {community}").format(community=contribution.membership.community.name)
    )

    if success:
        logger.info(f"Contribution notification email sent to {contribution.membership.user.email}")
        return True
    else:
        logger.error(f"Failed to send contribution notification email to {contribution.membership.user.email}")
        try:
            self.retry(countdown=self.default_retry_delay)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for contribution notification email.")
            return False
