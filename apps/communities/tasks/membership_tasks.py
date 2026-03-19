from celery import shared_task
import logging
from django.conf import settings
from apps.global_data.email import EmailUtil
from apps.communities.models import MembershipApplication
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_submitted_emails_task(self, application_id):
    """
    Send emails when a new membership application is submitted.
    1. To Community Admin/Owner
    2. To the Applicant (Member)
    """
    logger.info(f"Starting send_application_submitted_emails_task for application ID {application_id}")
    try:
        application = MembershipApplication.objects.select_related('community', 'user', 'community__created_by').get(id=application_id)
    except MembershipApplication.DoesNotExist:
        logger.error(f"MembershipApplication {application_id} not found.")
        return False

    email_util = EmailUtil()
    site_name = getattr(settings, 'SITE_NAME', 'Community Savings')
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    # 1. Email to Community Creator (Admin/Owner)
    admin = application.community.created_by
    if admin and admin.email:
        admin_context = {
            'community_name': application.community.name,
            'applicant_name': application.user.get_full_name or application.user.email,
            'applicant_email': application.user.email,
            'applied_role': application.get_applied_role_display(),
            'created_at': application.created.strftime('%Y-%m-%d %H:%M'),
            'admin_url': f"{site_url}/admin/communities/membershipapplication/{application.id}/change/",
            'site_name': site_name,
        }
        email_util.send_email_with_template(
            template='publics/emails/application_submitted_admin.html',
            context=admin_context,
            receivers=[admin.email],
            subject=_("New Membership Application for {community}").format(community=application.community.name)
        )
        logger.info(f"Admin notification email sent to {admin.email}")

    # 2. Email to Member (Applicant)
    if application.user.email:
        member_context = {
            'first_name': application.user.first_name or application.user.email.split('@')[0],
            'community_name': application.community.name,
            'site_name': site_name,
        }
        email_util.send_email_with_template(
            template='publics/emails/application_submitted_member.html',
            context=member_context,
            receivers=[application.user.email],
            subject=_("Application Received - {community}").format(community=application.community.name)
        )
        logger.info(f"Member confirmation email sent to {application.user.email}")
    
    return True

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_review_result_email_task(self, application_id):
    """
    Send email to member when their application is approved or rejected.
    """
    logger.info(f"Starting send_application_review_result_email_task for application ID {application_id}")
    try:
        application = MembershipApplication.objects.select_related('community', 'user').get(id=application_id)
    except MembershipApplication.DoesNotExist:
        logger.error(f"MembershipApplication {application_id} not found.")
        return False

    email_util = EmailUtil()
    site_name = getattr(settings, 'SITE_NAME', 'Community Savings')
    site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')

    context = {
        'first_name': application.user.first_name or application.user.email.split('@')[0],
        'community_name': application.community.name,
        'community_url': f"{site_url}/communities/{application.community.slug}/",
        'site_name': site_name,
    }

    if application.status == 'approved':
        template = 'publics/emails/application_approved.html'
        subject = _("Application Approved - {community}").format(community=application.community.name)
    elif application.status == 'rejected':
        template = 'publics/emails/application_rejected.html'
        subject = _("Update on Your Application - {community}").format(community=application.community.name)
        context['rejection_reason'] = application.rejection_reason
    else:
        logger.warning(f"Application {application_id} is in status {application.status}, no email sent.")
        return False

    if application.user.email:
        success = email_util.send_email_with_template(
            template=template,
            context=context,
            receivers=[application.user.email],
            subject=subject
        )
        if success:
            logger.info(f"Review result email sent to {application.user.email} (Status: {application.status})")
            return True
        else:
            logger.error(f"Failed to send review result email to {application.user.email}")
            try:
                self.retry(countdown=self.default_retry_delay)
            except self.MaxRetriesExceededError:
                logger.error("Max retries exceeded for review result email.")
                return False
    else:
        logger.warning(f"No email for user {application.user.id}, cannot send review result.")
        return False
