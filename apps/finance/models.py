from decimal import Decimal
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from apps.global_data.enum import CommunityFeatureType

from apps.users.models import SavingsBaseModel
from apps.global_data.enum import (
    ContributionStatus,
    FineType,
    FineStatus,
    LoanApplicationStatus,
    LoanStatus,
    CommunityFeatureType,
)
from apps.communities.models import Community, Membership, MembershipApplication


class FinancialSeason(SavingsBaseModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="financial_seasons")
    feature_type = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=CommunityFeatureType.choices
    )
    season_date = models.DateField(db_index=True, help_text="Example: 2025-01-01 for January 2025")
    title = models.CharField(max_length=100, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        unique_together = [("community", "feature_type", "season_date")]
        ordering = ["-season_date"]

    def __str__(self):
        return f"{self.community.name} - {self.season_date}"


class RegistrationPayment(SavingsBaseModel):
    application = models.OneToOneField(
        MembershipApplication,
        on_delete=models.CASCADE,
        related_name="registration_payment"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registration_payments_received"
    )
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"Registration Payment - {self.application.user.email}"

class ContributionCycle(SavingsBaseModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="contribution_cycles")
    season = models.ForeignKey(FinancialSeason, on_delete=models.CASCADE, related_name="contribution_cycles")
    feature_type = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=CommunityFeatureType.choices
    )
    title = models.CharField(max_length=255)
    due_date = models.DateField()
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2)
    is_special = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-due_date"]
    
    def clean(self):
        if not self.community.features.filter(
            feature_type=self.feature_type,
            is_active=True
        ).exists():
            raise ValidationError(f"{self.feature_type} is not enabled in this community.")


class Contribution(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="contributions")
    cycle = models.ForeignKey(ContributionCycle, on_delete=models.CASCADE, related_name="contributions")
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    paid_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ContributionStatus.choices, default=ContributionStatus.PENDING)
    payment_reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions_received"
    )
    comment = models.TextField(blank=True)
    signature = models.TextField(blank=True)

    class Meta:
        unique_together = [("membership", "cycle")]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["paid_at"]),
        ]

    def __str__(self):
        return f"{self.membership.user.fullname} - {self.cycle.title}"

    def clean(self):
        feature = self.cycle.feature_type or CommunityFeatureType.NJANGI
        if not self.membership.has_feature(feature):
            raise ValidationError(f"This member is not part of the {feature} system.")

class MemberFinanceSnapshot(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="finance_snapshots")
    season = models.ForeignKey(FinancialSeason, on_delete=models.CASCADE, related_name="member_finance_snapshots")

    net_income = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    entertainment_fees = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    savings = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    njangi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    project = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    others = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_finance_snapshots_recorded"
    )

    class Meta:
        unique_together = [("membership", "season")]

    def __str__(self):
        return f"{self.membership.user.full_name} - {self.season.season_date}"
    def clean(self):
        if not self.membership.has_feature(CommunityFeatureType.SAVINGS):
            raise ValidationError("Member is not part of savings.")

class NjangiRotation(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="njangi_rotations")
    season = models.ForeignKey(FinancialSeason, on_delete=models.CASCADE, related_name="njangi_rotations")
    position = models.PositiveIntegerField()

    class Meta:
        unique_together = [("season", "position"), ("season", "membership")]
        ordering = ["position"]

    def __str__(self):
        return f"{self.membership.user.get_full_name} - Pos {self.position}"

class NjangiBenefit(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="njangi_benefits")
    season = models.ForeignKey(FinancialSeason, on_delete=models.CASCADE, related_name="njangi_benefits")
    cycle = models.OneToOneField(ContributionCycle, on_delete=models.SET_NULL, null=True, blank=True, related_name="njangi_benefit")
    transaction_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    benefited_date = models.DateField()
    comment = models.TextField(blank=True)
    signature = models.TextField(blank=True)

    class Meta:
        unique_together = [("membership", "season")]

    def __str__(self):
        return f"Njangi Benefit - {self.membership.user.get_full_name}"
    def clean(self):
        if not self.membership.has_feature(CommunityFeatureType.NJANGI):
            raise ValidationError("Member is not eligible for Njangi benefits.")

class LoanProduct(SavingsBaseModel):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="loan_products")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    max_term_months = models.PositiveIntegerField(default=12)
    requires_guarantor = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("community", "name")]

    def __str__(self):
        return f"{self.name} - {self.community.name}"


class LoanApplication(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="loan_applications")
    loan_product = models.ForeignKey(LoanProduct, on_delete=models.PROTECT, related_name="applications")
    season = models.ForeignKey(FinancialSeason, on_delete=models.SET_NULL, null=True, blank=True, related_name="loan_applications")

    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    proposed_term_months = models.PositiveIntegerField()
    purpose = models.TextField()

    status = models.CharField(max_length=30, choices=LoanApplicationStatus.choices, default=LoanApplicationStatus.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_applications_decided"
    )
    rejection_reason = models.TextField(blank=True)

    recommended_score = models.PositiveIntegerField(null=True, blank=True)
    recommended_creditworthiness = models.CharField(max_length=20, blank=True)
    recommended_risk_band = models.CharField(max_length=20, blank=True)
    signature_data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.membership.user.fullname} - {self.amount_requested}"
    def clean(self):
        if not self.membership.has_feature(CommunityFeatureType.LOANS):
            raise ValidationError("Member is not eligible for loans.")
class LoanGuarantor(SavingsBaseModel):
    loan_application = models.ForeignKey(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name="guarantors"
    )
    guarantor_membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="guaranteed_loan_applications"
    )
    is_confirmed = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("loan_application", "guarantor_membership")]

    def __str__(self):
        return f"Guarantor - {self.guarantor_membership.user.full_name}"

class Loan(SavingsBaseModel):
    application = models.OneToOneField(LoanApplication, on_delete=models.CASCADE, related_name="loan")
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="loans")
    season = models.ForeignKey(FinancialSeason, on_delete=models.SET_NULL, null=True, blank=True, related_name="loans")

    amount_borrowed = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    interest_to_be_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    borrow_date = models.DateField()
    first_due_date = models.DateField(null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=LoanStatus.choices, default=LoanStatus.ACTIVE, db_index=True)

    id_card_number = models.CharField(max_length=100, blank=True)
    signature = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        indexes = [models.Index(fields=["status", "borrow_date"])]

    def __str__(self):
        return f"{self.membership.user.fullname} - {self.amount_borrowed}"

    @property
    def total_amount_plus_interest(self):
        return self.amount_borrowed + self.interest_to_be_paid

    @property
    def amount_left_to_pay(self):
        return self.total_amount_plus_interest - self.amount_paid

class LoanRepaymentSchedule(SavingsBaseModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="repayment_schedule")
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)

    class Meta:
        unique_together = [("loan", "installment_number")]
        ordering = ["installment_number"]

class LoanPayment(SavingsBaseModel):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    season = models.ForeignKey(FinancialSeason, on_delete=models.SET_NULL, null=True, blank=True, related_name="loan_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_payments_recorded"
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment {self.amount} - {self.loan_id}"

class Fine(SavingsBaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="fines")
    season = models.ForeignKey(FinancialSeason, on_delete=models.SET_NULL, null=True, blank=True, related_name="fines")
    fine_type = models.CharField(max_length=30, choices=FineType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True)
    issued_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=FineStatus.choices, default=FineStatus.UNPAID)

    related_contribution = models.ForeignKey(
        Contribution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fines"
    )
    related_loan = models.ForeignKey(
        Loan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fines"
    )

    def __str__(self):
        return f"{self.membership.user.full_name} - {self.fine_type}"

class FinePayment(SavingsBaseModel):
    fine = models.ForeignKey(Fine, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_at = models.DateTimeField()
    payment_reference = models.CharField(max_length=100, blank=True)
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fine_payments_received"
    )

    def __str__(self):
        return f"Fine Payment - {self.fine_id}"

class Wallet(SavingsBaseModel):
    membership = models.OneToOneField(
        "communities.Membership",
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.membership.user.get_full_name} Wallet"

class Transaction(SavingsBaseModel):
    membership = models.ForeignKey("communities.Membership", on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=50)  # deposit, withdrawal, loan, njangi

    reference = models.CharField(max_length=100, blank=True)

    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.membership.user.get_full_name} - {self.amount}"