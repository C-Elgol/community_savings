from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.global_data.enum import LoanStatus
from apps.users.models import SavingsBaseModel

# Constants for Decimal precision
MAX_DIGITS_LARGE = 15
MAX_DIGITS_MEDIUM = 12
MAX_DIGITS_SMALL = 10
DECIMAL_PLACES = 2

# Abstract mixin for models that are tied to a season
default_season_help = "Season date (e.g., 2025-01-01 for January 2025)."

class SeasonMixin(models.Model):
    season_date = models.DateField(help_text=default_season_help, db_index=True)

    class Meta:
        abstract = True

# Finance Record Model
class FinanceRecord(SavingsBaseModel, SeasonMixin):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='finance_records',
        help_text="The member whose finance record is being recorded.",
        db_index=True
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='recorded_finances',
        null=True,
        help_text="Staff member who recorded this finance entry."
    )
    net_income = models.DecimalField(max_digits=MAX_DIGITS_LARGE, decimal_places=DECIMAL_PLACES, default=0.00)
    entertainment_fees = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    savings = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    njangi = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    project = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    others = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)

    class Meta:
        verbose_name = _( "Finance Record" )
        verbose_name_plural = _( "Finance Records" )
        constraints = [
            models.UniqueConstraint(fields=["member", "season_date"], name="unique_member_season_finance")
        ]

    def __str__(self):
        return f"{self.member.get_full_name} - {self.season_date.strftime('%B %Y')}"

# Loan Management Model
class Loan(SavingsBaseModel, SeasonMixin):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loans',
        db_index=True
    )
    amount_borrowed = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES)
    amount_paid = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES, default=0.00)
    interest_to_be_paid = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    borrow_date = models.DateField(help_text="Date when the loan was taken.")
    status = models.CharField(max_length=10, choices=LoanStatus.choices, default=LoanStatus.UNPAID, db_index=True)
    id_card_number = models.CharField(max_length=50, blank=True)
    signature = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = _( "Loan" )
        verbose_name_plural = _( "Loans" )
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.member.get_full_name} - {self.amount_borrowed} - {self.status}"

    @property
    def amount_left_to_pay(self):
        return self.total_amount_plus_interest - self.amount_paid

    @property
    def total_amount_plus_interest(self):
        return self.amount_borrowed + self.interest_to_be_paid

# Loan Payment Model
class LoanPayment(SavingsBaseModel, SeasonMixin):
    loan = models.ForeignKey(
        'Loan',
        on_delete=models.CASCADE,
        related_name='payments',
        db_index=True
    )
    amount = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES)
    payment_date = models.DateField(help_text="Date of the payment.")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='loan_payments_recorded',
        null=True
    )
    comment = models.TextField(blank=True)

    class Meta:
        verbose_name = _( "Loan Payment" )
        verbose_name_plural = _( "Loan Payments" )
        ordering = ["-payment_date"]

    def __str__(self):
        return f"Payment of {self.amount} for {self.loan}"

# Njangi Management Model
class Njangi(SavingsBaseModel, SeasonMixin):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="njangi_records")
    position = models.CharField(max_length=50, blank=True)
    member_id_number = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES)
    benefited_date = models.DateField()
    id_card_number = models.CharField(max_length=50, blank=True)
    comment = models.TextField(blank=True)
    signature = models.TextField(blank=True)

    class Meta:
        verbose_name = _( "Njangi" )
        verbose_name_plural = _( "Njangis" )
        constraints = [
            models.UniqueConstraint(fields=["member_id_number", "season_date"], name="unique_member_season_njangi")
        ]

    def __str__(self):
        return f"Njangi for {self.user.get_full_name} - {self.amount}"

# Interest Calculation Model
class Interest(SavingsBaseModel, SeasonMixin):
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interests')
    total_savings = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES, default=0.00)
    interest_share = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)

    class Meta:
        verbose_name = _( "Interest" )
        verbose_name_plural = _( "Interests" )
        constraints = [
            models.UniqueConstraint(fields=["member", "season_date"], name="unique_member_season_interest")
        ]

    def __str__(self):
        return f"Interest for {self.member.get_full_name} - {self.interest_share}"

# Project Record Model
class ProjectRecord(SavingsBaseModel, SeasonMixin):
    amount_collected = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES)
    interest_collected = models.DecimalField(max_digits=MAX_DIGITS_SMALL, decimal_places=DECIMAL_PLACES, default=0.00)
    date_collected = models.DateField()
    comment = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='project_records', null=True)
    signature = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Signature"),
        help_text="Digital signature data for collection confirmation."
    )
    file_path = models.FileField(
        upload_to='uploads/projects/',
        blank=True,
        null=True,
        verbose_name=_("Uploaded File"),
        help_text="Uploaded project form (PDF, JPG, PNG)."
    )
    class Meta:
        verbose_name = _( "Project Record" )
        verbose_name_plural = _( "Project Records" )
        ordering = ["-date_collected"]

    def __str__(self):
        return f"Project Record - {self.amount_collected} on {self.date_collected}"

# Expenditure Model
class Expenditure(SavingsBaseModel, SeasonMixin):
    entertainment_spent = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES, default=0.00)
    other_expenditures = models.DecimalField(max_digits=MAX_DIGITS_MEDIUM, decimal_places=DECIMAL_PLACES, default=0.00)
    comment = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='recorded_expenditures', null=True)

    class Meta:
        verbose_name = _( "Expenditure" )
        verbose_name_plural = _( "Expenditures" )
        ordering = ["-season_date"]

    def __str__(self):
        return f"Expenditure - {self.entertainment_spent} + {self.other_expenditures} on {self.season_date.strftime('%B %Y')}"

# Collection Model
class Collection(SavingsBaseModel, SeasonMixin):
    member = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collections',
        help_text="The member who made the collection.",
        db_index=True
    )
    amount_collected = models.DecimalField(
        max_digits=MAX_DIGITS_MEDIUM,
        decimal_places=DECIMAL_PLACES,
        default=0.00,
        verbose_name=_("Amount Collected")
    )
    signature = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Signature"),
        help_text="Digital signature data for collection confirmation."
    )

    class Meta:
        verbose_name = _( "Collection" )
        verbose_name_plural = _( "Collections" )
        constraints = [
            models.UniqueConstraint(fields=["member", "season_date"], name="unique_member_season_collection")
        ]

    def __str__(self):
        return f"Collection of {self.amount_collected} for {self.member.get_full_name} - {self.season_date.strftime('%B %Y')}"