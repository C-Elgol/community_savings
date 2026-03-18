from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils.text import slugify

from apps.users.models import SavingsBaseModel
from apps.global_data.enum import (
    CommunityType,
    MembershipRole,
    MembershipStatus,
    RegistrationFeeMode,
    ContributionFrequency,
    CommunitySpaceRole,
    CommunitySpaceStatus,
)


class CommunitySpace(SavingsBaseModel):
    """
    Top-level tenant/workspace.
    Created by system admin and assigned to one or more users.
    Communities live inside a community space.
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to="community_spaces/logos/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Community space logo or identity image",
    )
    status = models.CharField(
        max_length=20,
        choices=CommunitySpaceStatus.choices,
        default=CommunitySpaceStatus.ACTIVE,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_community_spaces",
        help_text="System admin who created this community space.",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_community_spaces",
        help_text="Primary owner assigned to this community space.",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Community Space"
        verbose_name_plural = "Community Spaces"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CommunitySpaceMembership(SavingsBaseModel):
    """
    Controls which users can access which community spaces.
    """
    community_space = models.ForeignKey(
        CommunitySpace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_space_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=CommunitySpaceRole.choices,
        default=CommunitySpaceRole.VIEWER,
    )
    is_default = models.BooleanField(default=False)
    joined_at = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = [("community_space", "user")]
        indexes = [
            models.Index(fields=["community_space", "role"]),
            models.Index(fields=["user", "role"]),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.community_space.name} ({self.role})"


class Community(SavingsBaseModel):
    """
    Actual njangi/savings/cooperative/meeting group inside a space.
    """
    community_space = models.ForeignKey(
        CommunitySpace,
        on_delete=models.CASCADE,
        related_name="communities"
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    community_type = models.CharField(max_length=30, choices=CommunityType.choices, db_index=True)
    country = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=10, default="XAF")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    logo = models.ImageField(
        upload_to="communities/logos/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp"])],
        help_text="Community logo or identity image"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_communities",
    )

    class Meta:
        ordering = ["name"]
        unique_together = [
            ("community_space", "name"),
            ("community_space", "code"),
        ]
        indexes = [
            models.Index(fields=["community_space", "community_type"]),
            models.Index(fields=["community_space", "name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.community_space.name}-{self.name}")
        super().save(*args, **kwargs)

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

def validate_file_size(file):
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size > max_size:
        raise ValidationError("File size must be under 5MB.")

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

    # =========================
    # DOCUMENT TYPE SELECTION
    # =========================
    document_type = models.CharField(
        max_length=20,
        choices=[
            ("id_card", "National ID"),
            ("passport", "Passport"),
            ("driver_license", "Driver License"),
        ],
        default="id_card"
    )

    # =========================
    # DOCUMENT UPLOADS
    # =========================

    document_front = models.ImageField(
        upload_to="membership_applications/documents/front/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_file_size
        ],
        help_text="Upload front side of the selected document"
    )

    document_back = models.ImageField(
        upload_to="membership_applications/documents/back/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_file_size
        ],
        help_text="Upload back side (required for ID card & driver license)"
    )

    selfie_photo = models.ImageField(
        upload_to="membership_applications/selfies/",
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_file_size
        ],
        help_text="Optional selfie for identity verification"
    )

    # =========================
    # REGISTRATION FEES
    # =========================

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