from decimal import Decimal
from django.views.generic import View
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from apps.communities.models import Community, CommunityPolicy
from apps.global_data.enum import RegistrationFeeMode, ContributionFrequency

def _policy_data(policy):
    """Serialize a CommunityPolicy instance to a dict."""
    return {
        "id": str(policy.id),
        "registration_fee_mode": policy.registration_fee_mode,
        "registration_fee_mode_display": policy.get_registration_fee_mode_display(),
        "registration_fee_amount": str(policy.registration_fee_amount),
        "contribution_frequency": policy.contribution_frequency,
        "contribution_frequency_display": policy.get_contribution_frequency_display(),
        "default_contribution_amount": str(policy.default_contribution_amount),
        "late_contribution_fine_amount": str(policy.late_contribution_fine_amount),
        "absence_fine_amount": str(policy.absence_fine_amount),
        "minimum_membership_days_before_loan": policy.minimum_membership_days_before_loan,
        "max_active_loans_per_member": policy.max_active_loans_per_member,
        "max_loan_multiple_of_savings": str(policy.max_loan_multiple_of_savings),
        "default_interest_rate": str(policy.default_interest_rate),
        "requires_guarantor": policy.requires_guarantor,
        "minimum_guarantors": policy.minimum_guarantors,
    }

class CommunityPolicyDetailView(LoginRequiredMixin, View):
    """AJAX: Get policy details for a community."""
    def get(self, request, community_pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)
        
        try:
            community = Community.objects.get(pk=community_pk)
            # Try to get existing policy or return empty defaults
            policy, created = CommunityPolicy.objects.get_or_create(community=community)
            return JsonResponse({
                "success": True, 
                "policy": _policy_data(policy),
                "community_name": community.name
            })
        except Community.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Community not found."))}, status=404)

class CommunityPolicyUpdateView(LoginRequiredMixin, View):
    """AJAX: Create or Update community policy."""
    def post(self, request, community_pk, *args, **kwargs):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return JsonResponse({"success": False, "message": "Bad request."}, status=400)

        try:
            community = Community.objects.get(pk=community_pk)
            policy, created = CommunityPolicy.objects.get_or_create(community=community)
        except Community.DoesNotExist:
            return JsonResponse({"success": False, "message": str(_("Community not found."))}, status=404)

        data = request.POST
        errors = {}

        # Basic numeric validation helper
        def clean_decimal(val, field_name, default="0.00"):
            try:
                return Decimal(val.strip() or default)
            except (ValueError, TypeError, Exception):
                errors[field_name] = [str(_("Invalid amount."))]
                return Decimal(default)

        def clean_int(val, field_name, default=0):
            try:
                return int(val.strip() or default)
            except (ValueError, TypeError):
                errors[field_name] = [str(_("Invalid number."))]
                return default

        # Registration Fee
        policy.registration_fee_mode = data.get("registration_fee_mode", RegistrationFeeMode.NONE)
        policy.registration_fee_amount = clean_decimal(data.get("registration_fee_amount"), "registration_fee_amount")

        # Contributions
        policy.contribution_frequency = data.get("contribution_frequency", ContributionFrequency.MONTHLY)
        policy.default_contribution_amount = clean_decimal(data.get("default_contribution_amount"), "default_contribution_amount")

        # Fines
        policy.late_contribution_fine_amount = clean_decimal(data.get("late_contribution_fine_amount"), "late_contribution_fine_amount")
        policy.absence_fine_amount = clean_decimal(data.get("absence_fine_amount"), "absence_fine_amount")

        # Loans
        policy.minimum_membership_days_before_loan = clean_int(data.get("minimum_membership_days_before_loan"), "minimum_membership_days_before_loan", 30)
        policy.max_active_loans_per_member = clean_int(data.get("max_active_loans_per_member"), "max_active_loans_per_member", 1)
        policy.max_loan_multiple_of_savings = clean_decimal(data.get("max_loan_multiple_of_savings"), "max_loan_multiple_of_savings", "2.00")
        policy.default_interest_rate = clean_decimal(data.get("default_interest_rate"), "default_interest_rate", "5.00")
        policy.requires_guarantor = data.get("requires_guarantor") == "on" or data.get("requires_guarantor") == "true"
        policy.minimum_guarantors = clean_int(data.get("minimum_guarantors"), "minimum_guarantors", 1)

        if errors:
            return JsonResponse({"success": False, "message": str(_("Please fix the errors below.")), "errors": errors}, status=422)

        try:
            policy.save()
            return JsonResponse({
                "success": True, 
                "message": str(_("Policy for '%(name)s' updated successfully.") % {"name": community.name}),
                "policy": _policy_data(policy)
            })
        except Exception as e:
            return JsonResponse({"success": False, "message": str(_("An error occurred while saving policy."))}, status=500)
