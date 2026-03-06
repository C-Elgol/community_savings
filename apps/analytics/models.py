from decimal import Decimal
from django.db import models

from apps.common.models import BaseModel
from apps.common.enums import RiskBand, CreditworthinessLevel
from apps.communities.models import Membership
from apps.finance.models import FinancialSeason, LoanApplication


class MemberBehaviorSnapshot(BaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="behavior_snapshots")
    season = models.ForeignKey(FinancialSeason, on_delete=models.CASCADE, related_name="behavior_snapshots")

    contribution_consistency = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    repayment_punctuality = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    attendance_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    savings_stability = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    fine_frequency = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    default_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))
    debt_ratio = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.0000"))

    class Meta:
        unique_together = [("membership", "season")]

    def __str__(self):
        return f"Behavior Snapshot - {self.membership.user.full_name}"
class CreditProfile(BaseModel):
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, related_name="credit_profile")
    current_score = models.PositiveIntegerField(default=0, db_index=True)
    risk_band = models.CharField(max_length=20, choices=RiskBand.choices, default=RiskBand.LOW)
    creditworthiness = models.CharField(
        max_length=20,
        choices=CreditworthinessLevel.choices,
        default=CreditworthinessLevel.FAIR
    )
    recommended_max_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    probability_of_default = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))
    last_assessed_at = models.DateTimeField(null=True, blank=True)
    scoring_version = models.CharField(max_length=50, default="v1")

    def __str__(self):
        return f"{self.membership.user.full_name} - {self.current_score}"

class CreditProfile(BaseModel):
    membership = models.OneToOneField(Membership, on_delete=models.CASCADE, related_name="credit_profile")
    current_score = models.PositiveIntegerField(default=0, db_index=True)
    risk_band = models.CharField(max_length=20, choices=RiskBand.choices, default=RiskBand.LOW)
    creditworthiness = models.CharField(
        max_length=20,
        choices=CreditworthinessLevel.choices,
        default=CreditworthinessLevel.FAIR
    )
    recommended_max_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    probability_of_default = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.0000"))
    last_assessed_at = models.DateTimeField(null=True, blank=True)
    scoring_version = models.CharField(max_length=50, default="v1")

    def __str__(self):
        return f"{self.membership.user.full_name} - {self.current_score}"

class LoanRiskAssessment(BaseModel):
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name="risk_assessments")
    loan_application = models.OneToOneField(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name="risk_assessment"
    )

    score_used = models.PositiveIntegerField()
    risk_band = models.CharField(max_length=20, choices=RiskBand.choices)
    creditworthiness = models.CharField(max_length=20, choices=CreditworthinessLevel.choices)
    probability_of_default = models.DecimalField(max_digits=6, decimal_places=4)

    recommended_max_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    recommended_term_months = models.PositiveIntegerField(default=0)
    requires_guarantor = models.BooleanField(default=False)
    recommendation = models.CharField(max_length=100, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Risk Assessment - {self.membership.user.full_name}"