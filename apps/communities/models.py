from decimal import Decimal
from django.conf import settings
from django.db import models

from apps.users.models import SavingsBaseModel
from apps.global_data.enum import (
    CommunityType,
    MembershipRole,
    MembershipStatus,
    RegistrationFeeMode,
    ContributionFrequency,
)


class Community(SavingsBaseModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    description = models.TextField(blank=True)
    community_type = models.CharField(max_length=30, choices=CommunityType.choices, db_index=True)
    country = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=10, default="XAF")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_communities",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CommunityPolicy(SavingsBaseModel):
    community = models.OneToOneField(
        Community,
        on_delete=models.CASCADE,
        related_name="policy"
    )

    registration_fee_mode = models.CharField(
        max_length=20,
        choices=RegistrationFeeMode.choices,
        default=RegistrationFeeMode.NONE
    )
    registration_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    contribution_frequency = models.CharField(
        max_length=20,
        choices=ContributionFrequency.choices,
        default=ContributionFrequency.MONTHLY
    )
    default_contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    late_contribution_fine_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    absence_fine_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    minimum_membership_days_before_loan = models.PositiveIntegerField(default=30)
    max_active_loans_per_member = models.PositiveIntegerField(default=1)
    max_loan_multiple_of_savings = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("2.00"))
    default_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("5.00"))
    requires_guarantor = models.BooleanField(default=True)
    minimum_guarantors = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Policy - {self.community.name}"


class MembershipApplication(SavingsBaseModel):
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="membership_applications"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membership_applications"
    )

    applied_role = models.CharField(max_length=30, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.PENDING)

    registration_fee_required = models.BooleanField(default=False)
    registration_fee_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    registration_fee_paid = models.BooleanField(default=False)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_membership_applications"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        unique_together = [("community", "user")]
        indexes = [
            models.Index(fields=["community", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.community.name}"


class Membership(SavingsBaseModel):
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    role = models.CharField(max_length=30, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    status = models.CharField(max_length=20, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)

    joined_at = models.DateField()
    exited_at = models.DateField(null=True, blank=True)

    member_code = models.CharField(max_length=50, blank=True, db_index=True)
    member_id_number = models.CharField(max_length=50, blank=True)
    position = models.CharField(max_length=50, blank=True)

    id_card_number = models.CharField(max_length=100, blank=True)
    digital_signature = models.TextField(blank=True)

    application = models.OneToOneField(
        MembershipApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membership"
    )

    class Meta:
        unique_together = [("community", "user")]
        indexes = [
            models.Index(fields=["community", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.community.name}"